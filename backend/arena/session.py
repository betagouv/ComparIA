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


def increment_input_chars(key: str, ip: str, input_chars: int, pricey: bool) -> None:
    """
    Track input character count for rate limiting.

    Every message counts against the whole-pool budgets; only messages sent to
    an expensive model also count against the pricey ones. Each budget is
    counted twice, once per anonymous session and once per IP.

    Args:
        key: anonymous session hash
        ip: caller IP
        input_chars: Number of input characters to add to the counters
        pricey: whether an expensive model answered this message
    """
    client = get_redis_client()
    pools = ["all", "all_ip"] + (["pricey", "pricey_ip"] if pricey else [])
    for pool in pools:
        redis_key = _budget_key(pool, ip if pool.endswith("_ip") else key)
        client.incrby(redis_key, input_chars)
        # Set counter to expire in 2 hours (3600 * 2 seconds)
        client.expire(redis_key, 3600 * 2)


def is_ratelimited(key: str, ip: str) -> bool:
    """
    Check whether this session or its IP has spent any of its four budgets.

    Args:
        key: anonymous session hash
        ip: caller IP

    Returns:
        bool: True if any budget is exhausted
    """
    client = get_redis_client()
    budgets = (
        # Rate limit is 2x the configured limit for pricey models
        ("pricey", key, RATELIMIT_PRICEY_MODELS_INPUT * 2),
        ("pricey_ip", ip, RATELIMIT_PRICEY_MODELS_INPUT_PER_IP),
        ("all", key, RATELIMIT_ALL_MODELS_INPUT),
        ("all_ip", ip, RATELIMIT_ALL_MODELS_INPUT_PER_IP),
    )
    for pool, identity, limit in budgets:
        counter = client.get(_budget_key(pool, identity))
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
        client.incr(REDIS_BLOCKED_COUNT_KEY.format(ip=ip))
        client.expire(REDIS_BLOCKED_COUNT_KEY.format(ip=ip), 3600)
    except Exception as e:
        logger.error(f"[SESSION] Error incrementing blocked count for '{ip}': {e}")


def is_block_cooldown(ip: str) -> bool:
    """
    True if an IP has had too many guardrail-blocked prompts in the window.
    Fails open (returns False) on Redis error so a hiccup can't lock users out.
    """
    try:
        client = get_redis_client()
        counter = client.get(REDIS_BLOCKED_COUNT_KEY.format(ip=ip))
        assert not isinstance(counter, Awaitable)
        return bool(counter and int(counter) >= RATELIMIT_BLOCKED_PROMPTS_PER_HOUR)
    except Exception as e:
        logger.error(f"[SESSION] Error checking block cooldown for '{ip}': {e}")
        return False
