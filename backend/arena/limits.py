"""
How much text a person, and the network they send from, may have the models
handle in a window.

Each allowance is one Redis counter per pool and identity. The `all` pool counts
every character the models are sent and write. The `expensive` pool counts
what the expensive models cost, in millionths of a US dollar, estimated from
each model's prices. A model is expensive when its output price reaches the
threshold an admin sets. Each pool runs per anonymous session and per IP: the
session one is the one that matters, since people behind a shared NAT each get
their own; the IP one catches a client that drops its cookie to start over.

A spent `all` allowance stops every message. A spent `expensive` one only
keeps expensive models out of new comparisons: the conversations already
started with one may finish.

Each model's spend is also counted per Paris calendar day, across everyone,
in the same two steps. A model whose daily cap is reached rests until
midnight: new comparisons leave it out, the ones under way finish.

Routes call `read_status` for a cheap early answer, `Charge.reserve` to charge
what the models are sent before any of them is called, and `Charge.settle` to
add what they wrote once the turn is over.

The limits are settings an admin can change from /admin/limites, stored in the
app settings, with the RATELIMIT_* env values as defaults. Each process reads
them again at most every `RELOAD_SECONDS`, see `reload_settings`.
"""

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Collection, Iterable, Literal, Mapping, Protocol, Sequence, get_args
from uuid import UUID
from zoneinfo import ZoneInfo

from backend.config import settings
from backend.utils.user import ip_bucket
from utils.database.models.app_settings import AppSettings
from utils.database.settings import get_app_settings
from utils.storage.redis import (
    REDIS_BUDGET_KEY,
    REDIS_MODEL_DAY_KEY,
    get_redis_client,
)

logger = logging.getLogger("languia")

Pool = Literal["all", "expensive"]
POOLS: tuple[Pool, ...] = get_args(Pool)
Scope = Literal["session", "ip"]

# A counter expires 2 hours after the first message it counts, whatever comes
# after: the window is a fixed clock, not 2 hours of quiet.
WINDOW_SECONDS = 3600 * 2

# The prefix of an identity says which kind of counter it is.
_SCOPES: dict[str, Scope] = {"s": "session", "ip": "ip"}


def session_identity(anonymous_user_hash: str) -> str:
    return f"s:{anonymous_user_hash}"


def ip_identity(ip: str) -> str:
    return f"ip:{ip_bucket(ip)}"


# The pool names the counters had before this module, kept with the key so a
# deploy leaves what people spent in place. The key holds the identity without
# its prefix, as it always did. The expensive counters get new keys: the old
# ones counted characters, which would be wrong read as dollars.
_KEY_POOLS: dict[tuple[Pool, Scope], str] = {
    ("all", "session"): "all",
    ("all", "ip"): "all_ip",
    ("expensive", "session"): "expensive_usd",
    ("expensive", "ip"): "expensive_usd_ip",
}

# Model prices are in US dollars per million tokens, and a token is about four
# characters of text.
CHARS_PER_TOKEN = 4
# The expensive counters hold millionths of a dollar, so they stay whole
# numbers. At a price in dollars per million tokens, a token costs that many
# of them.
MICRO_USD = 1_000_000


def budget_key(pool: Pool, identity: str) -> str:
    return REDIS_BUDGET_KEY.format(
        pool=_KEY_POOLS[(pool, _scope(identity))], identity=identity.split(":", 1)[1]
    )


def _scope(identity: str) -> Scope:
    return _SCOPES[identity.split(":", 1)[0]]


LimitSetting = Literal[
    "all_per_session",
    "all_per_ip",
    "expensive_per_session",
    "expensive_per_ip",
    "expensive_price_out",
    "expected_answer_chars",
    "in_flight_per_network",
]
LIMIT_SETTINGS: tuple[LimitSetting, ...] = get_args(LimitSetting)

POOL_SETTINGS: dict[tuple[Pool, Scope], LimitSetting] = {
    ("all", "session"): "all_per_session",
    ("all", "ip"): "all_per_ip",
    ("expensive", "session"): "expensive_per_session",
    ("expensive", "ip"): "expensive_per_ip",
}

# How long a process keeps the stored settings before reading them again: a
# change reaches every pod within that time, without a read per message.
RELOAD_SECONDS = 30

# The settings in characters, whole numbers.
CHAR_SETTINGS: tuple[LimitSetting, ...] = (
    "all_per_session",
    "all_per_ip",
    "expected_answer_chars",
)
# The whole numbers: characters, and a count of turns. The others are in
# dollars.
WHOLE_SETTINGS: tuple[LimitSetting, ...] = (*CHAR_SETTINGS, "in_flight_per_network")

_stored: dict[LimitSetting, float] = {}
_loaded_at: float | None = None


def default(name: LimitSetting) -> float:
    """The RATELIMIT_* env value, in force while no admin has set one."""
    value: float = getattr(settings, f"RATELIMIT_{name.upper()}")
    return value


def setting(name: LimitSetting) -> float:
    """The value in force: the one an admin stored, else the default. Every
    read of a limit goes through here."""
    # The default is read on each call, so a test can move it.
    return _stored[name] if name in _stored else default(name)


def stored_settings(row: AppSettings) -> dict[LimitSetting, float]:
    """The settings an admin stored, leaving out those on their default."""
    stored: dict[LimitSetting, float] = {}
    for name in LIMIT_SETTINGS:
        value = getattr(row, f"limit_{name}")
        if value is not None:
            stored[name] = int(value) if name in WHOLE_SETTINGS else float(value)
    return stored


async def load_settings() -> None:
    """Read the stored settings now. When they cannot be read, the last ones
    read stay in force, the defaults on a fresh process."""
    global _stored, _loaded_at
    # Set first, so the requests that arrive meanwhile do not all read too.
    _loaded_at = time.monotonic()
    try:
        row: AppSettings = await get_app_settings()
    except Exception:
        logger.exception("Could not read the stored model allowances")
        return
    _stored = stored_settings(row)


async def reload_settings() -> None:
    """Read the stored settings again once `RELOAD_SECONDS` have passed. Runs
    before every arena route."""
    if _loaded_at is None or time.monotonic() - _loaded_at >= RELOAD_SECONDS:
        await load_settings()


def limit(pool: Pool, scope: Scope) -> int:
    """The limit in its counter's unit: characters, or millionths of a
    dollar."""
    value = setting(POOL_SETTINGS[(pool, scope)])
    return round(value * MICRO_USD) if pool == "expensive" else int(value)


def counted(pool: Pool, value: float) -> str:
    """A counter's value as people read it: characters, or dollars."""
    if pool == "expensive":
        return f"${value / MICRO_USD:,.4f}"
    return f"{int(value):,}"


def expected_answer_chars() -> int:
    return int(setting("expected_answer_chars"))


def in_flight_per_network() -> int:
    return int(setting("in_flight_per_network"))


class Priced(Protocol):
    """A model's prices, in US dollars per million tokens."""

    @property
    def price_in(self) -> float: ...

    @property
    def price_out(self) -> float: ...


def is_expensive(llm: Priced) -> bool:
    """Whether the model spends the expensive allowance: its output price
    reaches the threshold. A model priced 0 never does."""
    return llm.price_out > 0 and llm.price_out >= setting("expensive_price_out")


@dataclass(frozen=True)
class Identity:
    """Who a message counts against: the person, and the network they send
    from. Both are identities as the Redis keys spell them."""

    personal: str
    network: str

    @classmethod
    def of(cls, anonymous_user_hash: str, ip: str) -> "Identity":
        return cls(session_identity(anonymous_user_hash), ip_identity(ip))

    @property
    def identities(self) -> tuple[str, str]:
        return (self.personal, self.network)


@dataclass(frozen=True)
class Allowance:
    pool: Pool
    scope: Scope
    identity: str
    used: int
    limit: int
    # Seconds until the counter expires. None when there is no counter, or
    # when it has no expiry and so never resets.
    resets_in: int | None
    # When it expires, in Unix seconds: fixed when the window opens, so every
    # read tells the same time, where now + `resets_in` moves by a second.
    expires_at: int | None = None

    @property
    def spent(self) -> bool:
        # Strictly over: the last message let through may pass the limit by
        # its own size.
        return self.used > self.limit


@dataclass(frozen=True)
class LimitStatus:
    allowances: tuple[Allowance, ...]

    @property
    def spent(self) -> tuple[Allowance, ...]:
        return tuple(allowance for allowance in self.allowances if allowance.spent)

    def spent_in(self, pool: Pool) -> tuple[Allowance, ...]:
        return tuple(allowance for allowance in self.spent if allowance.pool == pool)

    @property
    def expensive_available(self) -> bool:
        """Whether a new draw may hold an expensive model."""
        return not self.spent_in("expensive")


class AllowanceSpent(Exception):
    """A message refused because an allowance it spends was already spent."""

    def __init__(self, spent: Sequence[Allowance]) -> None:
        super().__init__(", ".join(f"{a.pool} per {a.scope}" for a in spent))
        self.spent = tuple(spent)


@dataclass
class Call:
    """One model answering one side of a turn: the characters it was sent and
    wrote, its prices, and whether it spends the expensive allowance."""

    sent: int
    written: int = 0
    price_in: float = 0.0
    price_out: float = 0.0
    expensive: bool = False
    # Served from the answer cache: the provider was not called.
    cached: bool = False
    # The model, for its daily spend. None when the caller has no id, as in
    # a replay of a model the database no longer knows.
    llm_id: UUID | None = None

    @classmethod
    def of(cls, llm: Priced, sent: int, written: int = 0) -> "Call":
        """Whether the model is expensive is read once, here, so a threshold
        changed during a turn cannot reserve it one way and settle it the
        other."""
        llm_id = getattr(llm, "id", None)
        return cls(
            sent,
            written,
            llm.price_in,
            llm.price_out,
            is_expensive(llm),
            llm_id=llm_id if isinstance(llm_id, UUID) else None,
        )

    @property
    def micro_usd(self) -> int:
        """What the provider bills for this call, estimated from the prices
        and rounded up, in millionths of a dollar."""
        tokens_in, tokens_out = (
            self.sent / CHARS_PER_TOKEN,
            self.written / CHARS_PER_TOKEN,
        )
        # Rounded first, so a float a hair above a whole number does not
        # charge one more.
        return math.ceil(
            round(tokens_in * self.price_in + tokens_out * self.price_out, 6)
        )


def turn_cost(calls: Iterable[Call]) -> dict[Pool, int]:
    """
    What a turn spends of each pool. The whole one counts every character
    each model was sent and wrote, cached answers included: it bounds what one
    client can push through the arena. The expensive one counts what the
    expensive models cost, in millionths of a dollar, and nothing for a cached
    answer, which cost the provider nothing. A turn with no expensive model
    leaves that pool out, so a spent expensive allowance never refuses it.
    """
    calls = list(calls)
    cost: dict[Pool, int] = {"all": sum(call.sent + call.written for call in calls)}
    if expensive := [call for call in calls if call.expensive]:
        cost["expensive"] = sum(call.micro_usd for call in expensive if not call.cached)
    return cost


# A model's day follows the clock of the people using it: it ends at midnight
# in Paris, not in UTC, which would reset the caps at 1 or 2 in the morning.
DAY_ZONE = ZoneInfo("Europe/Paris")


def now() -> float:
    """The clock the daily caps read. Tests move it."""
    return time.time()


@dataclass(frozen=True)
class Day:
    """A Paris calendar day, as its keys spell it, and when it ends."""

    name: str
    ends_at: int

    @classmethod
    def at(cls, moment: float | None = None) -> "Day":
        local = datetime.fromtimestamp(now() if moment is None else moment, DAY_ZONE)
        tomorrow = datetime.combine(
            local.date() + timedelta(days=1), datetime.min.time(), DAY_ZONE
        )
        return cls(local.strftime("%Y%m%d"), int(tomorrow.timestamp()))

    @property
    def ends(self) -> datetime:
        return datetime.fromtimestamp(self.ends_at, timezone.utc)

    def ends_in(self) -> int:
        """Seconds until the day ends, on the same clock."""
        return max(0, math.ceil(self.ends_at - now()))


def model_day_key(llm_id: UUID, day: Day) -> str:
    return REDIS_MODEL_DAY_KEY.format(llm_id=llm_id, day=day.name)


# The fields of a model's day: millionths of a dollar, characters sent and
# written, answers, and the answers served from the cache.
DayField = Literal["usd", "in", "out", "answers", "cached"]


def day_cost(calls: Iterable[Call]) -> dict[UUID, dict[DayField, int]]:
    """What each model of these calls spends of its day. A cached answer
    costs nothing: the provider was not called."""
    cost: dict[UUID, dict[DayField, int]] = defaultdict(dict)
    for call in calls:
        if call.llm_id is None or call.cached:
            continue
        spent = cost[call.llm_id]
        spent["usd"] = spent.get("usd", 0) + call.micro_usd
        spent["in"] = spent.get("in", 0) + call.sent
        spent["out"] = spent.get("out", 0) + call.written
    return dict(cost)


def count_day(day: Day, changes: Mapping[UUID, Mapping[DayField, int]]) -> None:
    """
    Add to each model's day. The expiry goes with each change, in one
    transaction, so no day is left without one; it is the day's end, an
    absolute time, so sending it again moves nothing. A change that lands
    once the day is over, as a turn settled after midnight, removes that
    day at once.
    """
    changes = {
        llm_id: fields for llm_id, fields in changes.items() if any(fields.values())
    }
    if not changes:
        return
    pipe = get_redis_client().pipeline()
    for llm_id, fields in changes.items():
        key = model_day_key(llm_id, day)
        for name, amount in fields.items():
            if amount:
                pipe.hincrby(key, name, amount)
        pipe.expireat(key, day.ends_at)
    pipe.execute()


@dataclass(frozen=True)
class ModelDay:
    """What one model spent today, across everyone."""

    llm_id: UUID
    micro_usd: int = 0
    sent: int = 0
    written: int = 0
    answers: int = 0
    cached: int = 0


def read_model_days(
    llm_ids: Sequence[UUID], day: Day | None = None
) -> dict[UUID, ModelDay]:
    """Each model's day, in one round trip."""
    if not llm_ids:
        return {}
    day = day or Day.at()
    pipe = get_redis_client().pipeline()
    for llm_id in llm_ids:
        pipe.hgetall(model_day_key(llm_id, day))
    replies: list[dict[str, str]] = pipe.execute()
    return {
        llm_id: ModelDay(
            llm_id,
            micro_usd=int(fields.get("usd", 0)),
            sent=int(fields.get("in", 0)),
            written=int(fields.get("out", 0)),
            answers=int(fields.get("answers", 0)),
            cached=int(fields.get("cached", 0)),
        )
        for llm_id, fields in zip(llm_ids, replies)
    }


class Capped(Protocol):
    """A model and the most it may cost per day, in US dollars."""

    @property
    def id(self) -> UUID: ...

    @property
    def daily_usd_cap(self) -> float | None: ...


def is_resting(llm: Capped, spent: ModelDay) -> bool:
    """Whether the model's day is full: what it spent reached its cap."""
    if llm.daily_usd_cap is None:
        return False
    return spent.micro_usd >= round(llm.daily_usd_cap * MICRO_USD)


def resting_models(
    llms: Iterable[Capped], day: Day | None = None
) -> dict[UUID, datetime]:
    """
    The models whose daily cap is full, each with the moment it lifts. Read
    before a draw, like the allowances: first messages sent at once may each
    draw a model that only one of them fills, so a cap can be passed by a few
    turns, and by the conversations already under way, which finish.
    Reads nothing while no model has a cap.
    """
    day = day or Day.at()
    capped = [llm for llm in llms if llm.daily_usd_cap is not None]
    days = read_model_days([llm.id for llm in capped], day)
    return {llm.id: day.ends for llm in capped if is_resting(llm, days[llm.id])}


def read_counters(identities: Sequence[str]) -> LimitStatus:
    """Every allowance of these identities, in one round trip."""
    counters = [(pool, identity) for identity in identities for pool in POOLS]
    pipe = get_redis_client().pipeline()
    for pool, identity in counters:
        pipe.get(budget_key(pool, identity))
        pipe.ttl(budget_key(pool, identity))
        pipe.expiretime(budget_key(pool, identity))
    replies = pipe.execute()

    return LimitStatus(
        tuple(
            Allowance(
                pool=pool,
                scope=_scope(identity),
                identity=identity,
                used=int(used or 0),
                limit=limit(pool, _scope(identity)),
                resets_in=ttl if ttl >= 0 else None,
                expires_at=expires if expires >= 0 else None,
            )
            for (pool, identity), used, ttl, expires in zip(
                counters, replies[::3], replies[1::3], replies[2::3]
            )
        )
    )


def read_status(who: Identity) -> LimitStatus:
    """A cheap early answer. It charges nothing, so the routes still go
    through `reserve` before calling a model."""
    return read_counters(who.identities)


def reserve(
    who: Identity, cost: Mapping[Pool, int], refusing: Collection[Pool] = POOLS
) -> None:
    """
    Charge a message before any model sees it, or refuse it.

    The charge comes first and the check reads the total it returns, so
    requests sent at once each count the others, and a client that hangs up
    halfway through the answer has already paid. A message goes through when
    every allowance it spends was within its limit before it, so the last one
    can overshoot by its own size.

    Only the pools in `refusing` may refuse. The others are charged all the
    same: a conversation started with an expensive model finishes once that
    allowance is spent, and its turns still count against it.

    A counter's window starts with it and never moves: no charge, refund or
    settle pushes its expiry back. A network that sends all day gets a fresh
    allowance every two hours, and the reset time a person was told stays
    true while conversations finish.

    A refused message gets its characters back. It never reached a model, and
    left counted it would go on eating the allowances that were not spent yet,
    such as the IP one a whole school can share.

    Raises:
        AllowanceSpent: with each allowance that refused
    """
    # Every pool in the cost is checked, even at zero characters: a message
    # that counts for nothing must still meet a spent allowance.
    counters = [
        (pool, identity, chars)
        for pool, chars in cost.items()
        for identity in who.identities
    ]
    client = get_redis_client()

    pipe = client.pipeline()
    for pool, identity, chars in counters:
        key = budget_key(pool, identity)
        # A counter gets its expiry in the same step that creates it. Left to a
        # later call, a Redis error in between would leave a counter that never
        # expires, and an IP locked out for good.
        pipe.set(key, 0, ex=WINDOW_SECONDS, nx=True)
        pipe.incrby(key, chars)
    totals: list[int] = pipe.execute()[1::2]

    spent = [
        (pool, identity, total - chars)
        for (pool, identity, chars), total in zip(counters, totals)
        if total - chars > limit(pool, _scope(identity))
    ]
    refused = [counter for counter in spent if counter[0] in refusing]
    if not refused:
        return

    pipe = client.pipeline()
    for pool, identity, chars in counters:
        key = budget_key(pool, identity)
        pipe.decrby(key, chars)
        # Should the counter expire between the charge and the refund,
        # DECRBY brings it back below zero with no expiry: an allowance
        # that never resets. NX gives it the window and leaves any other
        # expiry alone.
        pipe.expire(key, WINDOW_SECONDS, nx=True)
    # When each spent allowance lifts, for the refusal to say so.
    for pool, identity, _used in refused:
        pipe.ttl(budget_key(pool, identity))
        pipe.expiretime(budget_key(pool, identity))
    replies = pipe.execute()

    # Two replies per counter (the refund and its expiry), then each refused
    # one's TTL and expiry time.
    refunded: list[int] = replies[: 2 * len(counters) : 2]
    ttls = replies[2 * len(counters) :: 2]
    expiries = replies[2 * len(counters) + 1 :: 2]
    # A counter that expired meanwhile took the refund below zero, which
    # would hand the new window more than its allowance. The window the
    # message was charged to is gone, so the refund goes with it.
    if below := [
        (budget_key(pool, identity), total)
        for (pool, identity, _chars), total in zip(counters, refunded)
        if total < 0
    ]:
        pipe = client.pipeline()
        for key, total in below:
            pipe.incrby(key, -total)
        pipe.execute()
    raise AllowanceSpent(
        [
            Allowance(
                pool=pool,
                scope=_scope(identity),
                identity=identity,
                used=used,
                limit=limit(pool, _scope(identity)),
                resets_in=ttl if ttl >= 0 else None,
                expires_at=expires if expires >= 0 else None,
            )
            for (pool, identity, used), ttl, expires in zip(refused, ttls, expiries)
        ]
    )


class Answer(Protocol):
    """What settling reads of a model's answer."""

    @property
    def content(self) -> str | None: ...

    @property
    def reasoning_content(self) -> str | None: ...

    @property
    def is_cached(self) -> bool: ...


def answer_chars(answer: Answer | None) -> int:
    """What a model wrote, its reasoning included: the provider bills both."""
    if answer is None:
        return 0
    return len(answer.content or "") + len(answer.reasoning_content or "")


class Charge:
    """
    What one turn spends, charged in two steps. `reserve` charges what the
    models are sent and what each is expected to write before either is
    called, and may refuse. `settle` brings it to what the turn really cost
    once it is over: what the models wrote, and what they were sent beyond
    the reservation, such as web search results found after it.
    """

    def __init__(self, who: Identity, calls: Mapping[str, Call]) -> None:
        self.who = who
        # The model answering each side now.
        self.calls = dict(calls)
        # Models that failed mid-turn and gave their side to a stand-in.
        self.replaced: list[Call] = []
        self.reserved = turn_cost(self.calls.values())
        # The day the turn counts for, kept so a turn settled after midnight
        # settles the day it reserved.
        self.day = Day.at()
        self.day_reserved = day_cost(self.calls.values())
        self.settled = False

    @classmethod
    def reserve(
        cls,
        who: Identity,
        calls: Mapping[str, Call],
        refusing: Collection[Pool] = POOLS,
    ) -> "Charge":
        """
        Charge what each side is sent and is expected to write, see
        `reserve`. Requests sent at once each meet the others' expected
        answers, so a burst cannot all pass on inputs alone.

        Raises:
            AllowanceSpent: with each allowance that refused
        """
        charge = cls(who, calls)
        reserve(who, charge.reserved, refusing)
        try:
            count_day(charge.day, charge.day_reserved)
        except Exception:
            # The allowances are charged. A model's day only decides the
            # next draws, so it fails open, like reading it.
            logger.exception("Could not count the models' day")
            charge.day_reserved = {}
        return charge

    def sending(self, pos: str, chars: int) -> None:
        """What this side is sent, counted on the messages as they go out."""
        self.calls[pos].sent = chars

    def replace(self, pos: str, llm: Priced, sent: int, written: int) -> None:
        """
        A stand-in takes this side over from a model that failed mid-turn.
        The failed model keeps what it was sent and what it wrote, since the
        provider bills both, and the stand-in is charged as itself.
        """
        failed = self.calls[pos]
        failed.written = written
        self.replaced.append(failed)
        self.calls[pos] = Call.of(llm, sent)

    def settle(self, answers: Mapping[str, Answer | None]) -> None:
        """
        Charge the turn's answers, however it ended: in full, on an error, or
        with the client gone, in which case what was written so far counts.
        The counters end at what the turn cost: an answer shorter than
        expected gives the rest back, a longer one adds to it. Nothing that
        was sent or written comes back on an error: one a client can provoke
        would buy whatever the models had written. A cached answer gives its
        side's share of the expensive pool back.

        It never refuses and never raises: the answers are already out. Nor
        does it move an expiry. SET NX gives a counter that expired meanwhile
        a new window and leaves every other expiry alone, so the reset time a
        person was told stays true, and no counter is left without one.
        Settling twice charges once.
        """
        if self.settled:
            return
        self.settled = True
        for pos, call in self.calls.items():
            answer = answers.get(pos)
            call.written = answer_chars(answer)
            call.cached = bool(answer and answer.is_cached)

        self._settle_day(answers)
        cost = turn_cost([*self.replaced, *self.calls.values()])
        owed = {
            pool: cost.get(pool, 0) - self.reserved.get(pool, 0)
            for pool in {*cost, *self.reserved}
        }
        counters = [
            (budget_key(pool, identity), chars)
            for pool, chars in owed.items()
            if chars
            for identity in self.who.identities
        ]
        try:
            client = get_redis_client()
            pipe = client.pipeline()
            for key, chars in counters:
                pipe.set(key, 0, ex=WINDOW_SECONDS, nx=True)
                pipe.incrby(key, chars)
            created = pipe.execute()[::2]
            # A refund on a counter that expired meanwhile would start the
            # new window below zero, below what the turn cost. The window the
            # turn was charged to is gone, so the refund goes with it.
            if undo := [
                (key, chars)
                for (key, chars), new in zip(counters, created)
                if new and chars < 0
            ]:
                pipe = client.pipeline()
                for key, chars in undo:
                    pipe.decrby(key, chars)
                pipe.execute()
        except Exception:
            logger.exception("Could not charge what the models wrote")

    def _settle_day(self, answers: Mapping[str, Answer | None]) -> None:
        """Bring each model's day to what the turn cost it, and count the
        answers it gave, the cached ones too."""
        cost = day_cost([*self.replaced, *self.calls.values()])
        changes: dict[UUID, dict[DayField, int]] = {}
        for llm_id in {*cost, *self.day_reserved}:
            spent, reserved = cost.get(llm_id, {}), self.day_reserved.get(llm_id, {})
            changes[llm_id] = {
                name: spent.get(name, 0) - reserved.get(name, 0)
                for name in ("usd", "in", "out")
            }
        for pos, call in self.calls.items():
            if call.llm_id is None or answers.get(pos) is None:
                continue
            fields = changes.setdefault(call.llm_id, {})
            fields["answers"] = fields.get("answers", 0) + 1
            fields["cached"] = fields.get("cached", 0) + int(call.cached)
        try:
            count_day(self.day, changes)
        except Exception:
            logger.exception("Could not count the models' day")


def reset_counters(identities: Sequence[str]) -> int:
    """Forget what these identities spent. Returns how many counters went."""
    keys = [budget_key(pool, identity) for identity in identities for pool in POOLS]
    return int(get_redis_client().delete(*keys))
