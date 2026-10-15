"""
How many turns one network may have the models answer at once.

A turn is charged what its models are sent and a typical answer before they
are called, and what they really wrote only once it is over. Hundreds of
messages sent at once would all pass the allowances before any long answer
was counted. Holding each network to a few dozen turns at a time bounds what
such a burst can spend.

Each turn holds a slot from before its models are called until its answer is
sent, or it fails. A slot is a member of one sorted set per network, scored
with the moment it lapses, so a request that crashed before giving its slot
back holds it `SLOT_SECONDS` at most. The cap is the same for every model and
every person on the network: a refusal says nothing about any pair.
"""

import logging
import time
from dataclasses import dataclass
from typing import Iterator
from uuid import uuid4

from fastapi import Request
from redis.exceptions import RedisError

from backend.arena.limits import in_flight_per_network, network_identity
from backend.errors import TooManyAtOnceError
from backend.utils.user import get_ip
from utils.storage.redis import REDIS_IN_FLIGHT_KEY, get_redis_client

logger = logging.getLogger("languia")

# Longer than a turn takes: two answers of 16,384 tokens stream in a couple of
# minutes, and a model that stops sending is dropped after 30 seconds.
SLOT_SECONDS = 300


def now() -> float:
    """The clock slots lapse on. Tests move it."""
    return time.time()


class TooManyAtOnce(Exception):
    """The network already has as many turns answering as it may."""


@dataclass
class TurnSlot:
    """One turn answering for a network, until `release`."""

    key: str
    member: str | None
    released: bool = False

    @classmethod
    def take(cls, network: str) -> "TurnSlot":
        """
        Take a slot for a turn of this network, an identity as `network_identity`
        spells it.

        Counted after the slot is added, so requests sent at once each count
        the others. Should Redis fail, the turn goes on with no slot: the
        allowances still charge it, and refuse it when Redis is down.

        Raises:
            TooManyAtOnce: when the network's slots are all taken
        """
        key = REDIS_IN_FLIGHT_KEY.format(network=network.split(":", 1)[1])
        member = uuid4().hex
        moment = now()
        try:
            client = get_redis_client()
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, "-inf", moment)
            pipe.zadd(key, {member: moment + SLOT_SECONDS})
            pipe.zcard(key)
            # The set goes with its last slot.
            pipe.expire(key, SLOT_SECONDS)
            taken = int(pipe.execute()[2])
        except RedisError:
            logger.exception("Could not count the turns answering at once")
            return cls(key, None)
        slot = cls(key, member)
        if taken > in_flight_per_network():
            slot.release()
            raise TooManyAtOnce()
        return slot

    def release(self) -> None:
        """Give the slot back. Never raises; a slot not given back lapses."""
        if self.released or self.member is None:
            return
        self.released = True
        try:
            get_redis_client().zrem(self.key, self.member)
        except RedisError:
            logger.exception("Could not give back a turn's slot")


def hold_turn_slot(request: Request) -> Iterator[None]:
    """
    A route dependency: the turn holds a slot of its network from before its
    models are called until its answer is sent, or the route fails. FastAPI
    runs what follows the yield once the streamed response is over.

    Raises:
        TooManyAtOnceError: a 429 the arena shows as "try again in a few
            seconds"
    """
    try:
        slot = TurnSlot.take(network_identity(get_ip(request)))
    except TooManyAtOnce:
        logger.warning(
            "Refused a turn: too many answering at once on its network",
            extra={"request": request},
        )
        raise TooManyAtOnceError()
    try:
        yield
    finally:
        slot.release()
