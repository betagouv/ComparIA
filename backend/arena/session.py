"""
Arena session management for comparisons state in Redis.

Handles storing and retrieving some comparison metadata not saved in db during
active arena sessions.
"""

import logging
import uuid
from typing import Awaitable

from pydantic import BaseModel, ValidationError

from backend.config import (
    RATELIMIT_ALL_MODELS_INPUT,
    RATELIMIT_ALL_MODELS_INPUT_PER_IP,
    RATELIMIT_BLOCKED_PROMPTS_PER_HOUR,
    RATELIMIT_PRICEY_MODELS_INPUT,
    RATELIMIT_PRICEY_MODELS_INPUT_PER_IP,
)
from backend.utils.user import ip_bucket
from utils.storage.redis import (
    REDIS_BLOCKED_COUNT_KEY,
    REDIS_COMPARISON_KEY,
    REDIS_USER_CHAR_COUNT,
    get_redis_client,
)

logger = logging.getLogger("languia")


class ComparisonMetadata(BaseModel):
    id: uuid.UUID
    is_streaming: bool


def store_comparison_metadata(id: uuid.UUID, is_streaming: bool) -> None:
    expire_time = 86400  # 24 hours

    try:
        client = get_redis_client()
        client.setex(
            REDIS_COMPARISON_KEY.format(id=id),
            expire_time,
            ComparisonMetadata(id=id, is_streaming=is_streaming).model_dump_json(),
        )
        logger.info(f"[SESSION] Stored comparison '{id}' metadata.")
    except Exception as e:
        logger.error(f"[SESSION] Error storing comparison '{id}' metadata: {e}")
        raise


def retreive_comparison_metadata(id: uuid.UUID) -> ComparisonMetadata:
    try:
        client = get_redis_client()
        data = client.get(REDIS_COMPARISON_KEY.format(id=id))
        assert not isinstance(data, Awaitable)
        if not data:
            logger.warning(f"[SESSION] comparison metadata not found: '{id}'.")
            raise ValueError(f"Comparison metadata not found: '{id}'.")

        logger.info(f"[SESSION] Retrieved comparison '{id}' metadata.")

        return ComparisonMetadata.model_validate_json(data)

    except ValidationError as e:
        logger.error(f"[SESSION] Error decoding comparison '{id}' metadata.: {e}")
        raise ValueError(f"Invalid comparison '{id}' metadata.")
    except Exception as e:
        logger.error(f"[SESSION] Error retrieving comparison '{id}' metadata.: {e}")
        raise


# FIXME unused?
def delete_session(id: uuid.UUID) -> bool:
    """
    Delete comparison metadata from Redis.

    Args:
        id: Unique comparison identifier

    Returns:
        bool: True if metadata was deleted, False if it didn't exist
    """
    try:
        client = get_redis_client()
        deleted = client.delete(REDIS_COMPARISON_KEY.format(id=id))
        logger.info(f"[SESSION] Deleted comparison '{id}' metadata: {bool(deleted)}")
        return bool(deleted)
    except Exception as e:
        logger.error(f"[SESSION] Error deleting comparison '{id}' metadata: {e}")
        return False


def _budget_key(pool: str, identity: str) -> str:
    """One Redis counter per (pool, identity). The pool goes in the key because
    the four budgets share the one key template."""
    return REDIS_USER_CHAR_COUNT.format(key=f"{pool}:{identity}")


# Counters expire 2 hours after the last message they let through.
BUDGET_TTL_SECONDS = 3600 * 2


def _budgets(key: str, ip: str, pricey: bool = True) -> list[tuple[str, int]]:
    """
    The Redis counter and limit of each budget a message spends.

    Every message counts against the whole-pool budgets; only messages sent to
    an expensive model also count against the pricey ones. Each budget is
    counted twice, once per anonymous session and once per IP.
    """
    budgets = (
        # Rate limit is 2x the configured limit for pricey models
        ("pricey", key, RATELIMIT_PRICEY_MODELS_INPUT * 2),
        ("pricey_ip", ip_bucket(ip), RATELIMIT_PRICEY_MODELS_INPUT_PER_IP),
        ("all", key, RATELIMIT_ALL_MODELS_INPUT),
        ("all_ip", ip_bucket(ip), RATELIMIT_ALL_MODELS_INPUT_PER_IP),
    )
    return [
        (_budget_key(pool, identity), limit)
        for pool, identity, limit in budgets
        if pricey or not pool.startswith("pricey")
    ]


def reserve_input_chars(key: str, ip: str, input_chars: int, pricey: bool) -> bool:
    """
    Charge a message's characters before any model sees it, or refuse it.

    The charge comes first and the check reads the total it returns, so
    requests sent at once each count the others, and a client that hangs up
    halfway through the answer has already paid. A message goes through when
    every budget it spends was within its limit before it: the rule the
    counters always had, so the last message can overshoot by its own length.

    A refused message gets its characters back. It never reached a model, and
    left counted it would go on eating the budgets that were not spent yet,
    such as the IP one a whole school can share.

    Args:
        key: anonymous session hash
        ip: caller IP
        input_chars: Number of input characters the message spends
        pricey: whether an expensive model will answer this message

    Returns:
        bool: True if the message was charged and may go to the models
    """
    client = get_redis_client()
    budgets = _budgets(key, ip, pricey)

    pipe = client.pipeline()
    for redis_key, _limit in budgets:
        # A counter gets its expiry in the same step that creates it. Left to a
        # later call, a Redis error in between would leave a counter that never
        # expires, and an IP locked out for good.
        pipe.set(redis_key, 0, ex=BUDGET_TTL_SECONDS, nx=True)
        pipe.incrby(redis_key, input_chars)
    totals: list[int] = pipe.execute()[1::2]

    allowed = all(
        total - input_chars <= limit for total, (_, limit) in zip(totals, budgets)
    )
    pipe = client.pipeline()
    for redis_key, _limit in budgets:
        # A refused message leaves the window where it was.
        if allowed:
            pipe.expire(redis_key, BUDGET_TTL_SECONDS)
        else:
            pipe.decrby(redis_key, input_chars)
    pipe.execute()
    return allowed


def is_ratelimited(key: str, ip: str) -> bool:
    """
    Check whether this session or its IP has spent any of its four budgets.

    Only a cheap early answer: it charges nothing, so the routes still go
    through `reserve_input_chars` before calling a model.

    Args:
        key: anonymous session hash
        ip: caller IP

    Returns:
        bool: True if any budget is exhausted
    """
    client = get_redis_client()
    for redis_key, limit in _budgets(key, ip):
        counter = client.get(redis_key)
        assert not isinstance(counter, Awaitable)
        if counter and int(counter) > limit:
            return True
    return False


def increment_blocked_prompts(ip: str) -> None:
    """
    Count guardrail-blocked prompts per IP in a rolling 1h window (cooldown for
    abuse / jailbreak probing). Fails open: a Redis error must not break the flow.
    """
    try:
        client = get_redis_client()
        key = REDIS_BLOCKED_COUNT_KEY.format(ip=ip_bucket(ip))
        client.incr(key)
        client.expire(key, 3600)
    except Exception as e:
        logger.error(f"[SESSION] Error incrementing blocked count: {e}")


def is_block_cooldown(ip: str) -> bool:
    """
    True if an IP has had too many guardrail-blocked prompts in the window.
    Fails open (returns False) on Redis error so a hiccup can't lock users out.
    """
    try:
        client = get_redis_client()
        counter = client.get(REDIS_BLOCKED_COUNT_KEY.format(ip=ip_bucket(ip)))
        assert not isinstance(counter, Awaitable)
        return bool(counter and int(counter) >= RATELIMIT_BLOCKED_PROMPTS_PER_HOUR)
    except Exception as e:
        logger.error(f"[SESSION] Error checking block cooldown: {e}")
        return False
