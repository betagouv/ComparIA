"""
How much text a person, and the network they send from, may have the models
handle in a window.

Each allowance is one Redis counter per pool and identity. The `all` pool counts
every character the models are sent and write. The `expensive` pool counts
only the expensive models' characters, each as many times as the model's cost
weight. Each pool runs per anonymous session and per IP: the session one is
the one that matters, since people behind a shared NAT each get their own; the
IP one catches a client that drops its cookie to start over.

A spent `all` allowance stops every message. A spent `expensive` one only
keeps expensive models out of new comparisons: the conversations already
started with one may finish.

Routes call `read_status` for a cheap early answer, `Charge.reserve` to charge
what the models are sent before any of them is called, and `Charge.settle` to
add what they wrote once the turn is over.
"""

import logging
import math
from dataclasses import dataclass
from typing import Collection, Iterable, Literal, Mapping, Protocol, Sequence, get_args

from backend.config import settings
from backend.utils.user import ip_bucket
from utils.storage.redis import REDIS_BUDGET_KEY, get_redis_client

logger = logging.getLogger("languia")

Pool = Literal["all", "expensive"]
POOLS: tuple[Pool, ...] = get_args(Pool)
Scope = Literal["session", "ip"]

# Counters expire 2 hours after the last message they let through.
WINDOW_SECONDS = 3600 * 2

# The prefix of an identity says which kind of counter it is.
_SCOPES: dict[str, Scope] = {"s": "session", "ip": "ip"}


def session_identity(anonymous_user_hash: str) -> str:
    return f"s:{anonymous_user_hash}"


def ip_identity(ip: str) -> str:
    return f"ip:{ip_bucket(ip)}"


# The pool names the counters had before this module, kept with the key so a
# deploy leaves what people spent in place. The key holds the identity without
# its prefix, as it always did.
_KEY_POOLS: dict[tuple[Pool, Scope], str] = {
    ("all", "session"): "all",
    ("all", "ip"): "all_ip",
    ("expensive", "session"): "pricey",
    ("expensive", "ip"): "pricey_ip",
}


def budget_key(pool: Pool, identity: str) -> str:
    return REDIS_BUDGET_KEY.format(
        pool=_KEY_POOLS[(pool, _scope(identity))], identity=identity.split(":", 1)[1]
    )


def _scope(identity: str) -> Scope:
    return _SCOPES[identity.split(":", 1)[0]]


def _limit(pool: Pool, scope: Scope) -> int:
    # Read on each call, so a test can move them.
    return {
        ("all", "session"): settings.RATELIMIT_ALL_PER_SESSION,
        ("all", "ip"): settings.RATELIMIT_ALL_PER_IP,
        ("expensive", "session"): settings.RATELIMIT_EXPENSIVE_PER_SESSION,
        ("expensive", "ip"): settings.RATELIMIT_EXPENSIVE_PER_IP,
    }[(pool, scope)]


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
    wrote, and how many times an ordinary model it costs."""

    weight: float
    sent: int
    written: int = 0
    # Served from the answer cache: the provider was not called.
    cached: bool = False


def turn_cost(calls: Iterable[Call]) -> dict[Pool, int]:
    """
    What a turn spends of each pool. The whole one counts every character
    each model was sent and wrote, cached answers included: it bounds what one
    client can push through the arena. The expensive one counts the expensive
    models only, each character `weight` times, and nothing for a cached
    answer, which cost the provider nothing. A turn with no expensive model
    leaves that pool out, so a spent expensive allowance never refuses it.
    """
    calls = list(calls)
    cost: dict[Pool, int] = {"all": sum(call.sent + call.written for call in calls)}
    if expensive := [call for call in calls if call.weight > 1]:
        cost["expensive"] = sum(
            math.ceil(call.weight * (call.sent + call.written))
            for call in expensive
            if not call.cached
        )
    return cost


def read_counters(identities: Sequence[str]) -> LimitStatus:
    """Every allowance of these identities, in one round trip."""
    counters = [(pool, identity) for identity in identities for pool in POOLS]
    pipe = get_redis_client().pipeline()
    for pool, identity in counters:
        pipe.get(budget_key(pool, identity))
        pipe.ttl(budget_key(pool, identity))
    replies = pipe.execute()

    return LimitStatus(
        tuple(
            Allowance(
                pool=pool,
                scope=_scope(identity),
                identity=identity,
                used=int(used or 0),
                limit=_limit(pool, _scope(identity)),
                resets_in=ttl if ttl >= 0 else None,
            )
            for (pool, identity), used, ttl in zip(
                counters, replies[::2], replies[1::2]
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
    allowance is spent, and its turns still count against it. A spent
    allowance keeps its expiry, so the reset time the person was told stays
    true while such conversations finish.

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
        if total - chars > _limit(pool, _scope(identity))
    ]
    refused = [counter for counter in spent if counter[0] in refusing]
    over = {(pool, identity) for pool, identity, _used in spent}
    pipe = client.pipeline()
    for pool, identity, chars in counters:
        key = budget_key(pool, identity)
        # A refused message leaves the window where it was.
        if refused:
            pipe.decrby(key, chars)
            # Should the counter expire between the charge and the refund,
            # DECRBY brings it back below zero with no expiry: an allowance
            # that never resets. NX gives it the window and leaves any other
            # expiry alone.
            pipe.expire(key, WINDOW_SECONDS, nx=True)
        elif (pool, identity) not in over:
            pipe.expire(key, WINDOW_SECONDS)
    # When each spent allowance lifts, for the refusal to say so.
    for pool, identity, _used in refused:
        pipe.ttl(budget_key(pool, identity))
    replies = pipe.execute()

    if refused:
        # Two replies per counter (the refund and its expiry), then the TTLs.
        ttls = replies[2 * len(counters) :]
        raise AllowanceSpent(
            [
                Allowance(
                    pool=pool,
                    scope=_scope(identity),
                    identity=identity,
                    used=used,
                    limit=_limit(pool, _scope(identity)),
                    resets_in=ttl if ttl >= 0 else None,
                )
                for (pool, identity, used), ttl in zip(refused, ttls)
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
        return charge

    def sending(self, pos: str, chars: int) -> None:
        """What this side is sent, counted on the messages as they go out."""
        self.calls[pos].sent = chars

    def replace(self, pos: str, weight: float, sent: int, written: int) -> None:
        """
        A stand-in takes this side over from a model that failed mid-turn.
        The failed model keeps what it was sent and what it wrote, since the
        provider bills both, and the stand-in is charged as itself.
        """
        failed = self.calls[pos]
        failed.written = written
        self.replaced.append(failed)
        self.calls[pos] = Call(weight, sent)

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


def reset_counters(identities: Sequence[str]) -> int:
    """Forget what these identities spent. Returns how many counters went."""
    keys = [budget_key(pool, identity) for identity in identities for pool in POOLS]
    return int(get_redis_client().delete(*keys))
