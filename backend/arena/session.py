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
    RATELIMIT_BLOCKED_PROMPTS_PER_HOUR,
    RATELIMIT_PRICEY_MODELS_INPUT,
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


def increment_input_chars(key: str, input_chars: int) -> None:
    """
    Track input character count per anonymous session for rate limiting.

    Increments a counter in Redis for the given key and sets expiry to 2 hours.
    This prevents users from overloading expensive model APIs.

    Args:
        key: Rate-limit identity (anonymous session hash)
        input_chars: Number of input characters to add to counter
    """
    client = get_redis_client()
    client.incrby(REDIS_USER_CHAR_COUNT.format(key=key), input_chars)
    # Set counter to expire in 2 hours (3600 * 2 seconds)
    client.expire(REDIS_USER_CHAR_COUNT.format(key=key), 3600 * 2)


def is_ratelimited(key: str) -> bool:
    """
    Check if an anonymous session has exceeded the rate limit for expensive models.

    Args:
        key: Rate-limit identity (anonymous session hash)

    Returns:
        bool: True if the key has exceeded the limit (2x RATELIMIT_PRICEY_MODELS_INPUT)
    """
    client = get_redis_client()
    counter = client.get(REDIS_USER_CHAR_COUNT.format(key=key))
    assert not isinstance(counter, Awaitable)
    # Rate limit is 2x the configured limit for pricey models
    if counter and int(counter) > RATELIMIT_PRICEY_MODELS_INPUT * 2:
        return True
    else:
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
        logger.error(
            "Failed to increment blocked prompt count",
            extra={
                "extra": {
                    "event": "guardrail.blocked_count_failed",
                    "exception_type": type(e).__name__,
                }
            },
        )


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
        logger.error(
            "Failed to check blocked prompt cooldown",
            extra={
                "extra": {
                    "event": "guardrail.blocked_cooldown_failed",
                    "exception_type": type(e).__name__,
                }
            },
        )
        return False
