"""
How much text a person, and the network they send from, may have the models
handle in a window.

Each allowance is one Redis counter per pool and identity. The `all` pool counts
every message, the `expensive` pool only the messages an expensive model
answers. Each pool runs per anonymous session and per IP: the session one is
the one that matters, since people behind a shared NAT each get their own; the
IP one catches a client that drops its cookie to start over.

Routes call `read_status` for a cheap early answer and `reserve` to charge a
message before any model sees it.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Mapping, Sequence, get_args
from uuid import UUID

from backend.config import settings
from backend.utils.user import ip_bucket
from utils.storage.redis import REDIS_BUDGET_KEY, get_redis_client

if TYPE_CHECKING:
    from backend.llms.data import LLMsData

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


class AllowanceSpent(Exception):
    """A message refused because an allowance it spends was already spent."""

    def __init__(self, refused: Sequence[tuple[Pool, Scope]]) -> None:
        super().__init__(", ".join(f"{pool} per {scope}" for pool, scope in refused))
        self.refused = tuple(refused)


def message_cost(
    text: str, llm_ids: tuple[UUID, UUID], llms_data: "LLMsData"
) -> dict[Pool, int]:
    """A message costs its length, on the expensive pool too when either
    model is expensive. A cheap pair leaves that pool out, so a spent
    expensive allowance never refuses it."""
    cost: dict[Pool, int] = {"all": len(text)}
    if any(llm_id in llms_data.pricey_models for llm_id in llm_ids):
        cost["expensive"] = len(text)
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


def reserve(who: Identity, cost: Mapping[Pool, int]) -> None:
    """
    Charge a message before any model sees it, or refuse it.

    The charge comes first and the check reads the total it returns, so
    requests sent at once each count the others, and a client that hangs up
    halfway through the answer has already paid. A message goes through when
    every allowance it spends was within its limit before it, so the last one
    can overshoot by its own size.

    A refused message gets its characters back. It never reached a model, and
    left counted it would go on eating the allowances that were not spent yet,
    such as the IP one a whole school can share.

    Raises:
        AllowanceSpent: with the pool and scope of each allowance that refused
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

    refused = [
        (pool, _scope(identity))
        for (pool, identity, chars), total in zip(counters, totals)
        if total - chars > _limit(pool, _scope(identity))
    ]
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
        else:
            pipe.expire(key, WINDOW_SECONDS)
    pipe.execute()

    if refused:
        raise AllowanceSpent(refused)


def reset_counters(identities: Sequence[str]) -> int:
    """Forget what these identities spent. Returns how many counters went."""
    keys = [budget_key(pool, identity) for identity in identities for pool in POOLS]
    return int(get_redis_client().delete(*keys))
