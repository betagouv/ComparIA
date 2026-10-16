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
    RATELIMIT_SENT_WARNINGS_PER_HOUR,
)
from backend.utils.user import ip_bucket
from utils.storage.redis import (
    REDIS_BLOCKED_COUNT_KEY,
    REDIS_COMPARISON_KEY,
    REDIS_SENT_WARNINGS_KEY,
    REDIS_UNVOTED_KEY,
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


def increment_sent_warnings(session: str) -> None:
    """Count a warning a session answered with "send anyway", in a rolling
    hour. Fails open like the block count."""
    try:
        client = get_redis_client()
        key = REDIS_SENT_WARNINGS_KEY.format(session=session)
        client.incr(key)
        client.expire(key, 3600)
    except Exception as e:
        logger.error(f"[SESSION] Error incrementing sent warnings: {e}")


def is_warning_cooldown(session: str) -> bool:
    try:
        client = get_redis_client()
        counter = client.get(REDIS_SENT_WARNINGS_KEY.format(session=session))
        assert not isinstance(counter, Awaitable)
        return bool(counter and int(counter) >= RATELIMIT_SENT_WARNINGS_PER_HOUR)
    except Exception as e:
        logger.error(f"[SESSION] Error checking sent warnings: {e}")
        return False


def increment_unvoted(session: str) -> None:
    """Count a comparison a session started, until it votes. Fails open."""
    try:
        client = get_redis_client()
        key = REDIS_UNVOTED_KEY.format(session=session)
        client.incr(key)
        client.expire(key, 86400)
    except Exception as e:
        logger.error(f"[SESSION] Error incrementing unvoted comparisons: {e}")


def clear_unvoted(session: str) -> None:
    try:
        get_redis_client().delete(REDIS_UNVOTED_KEY.format(session=session))
    except Exception as e:
        logger.error(f"[SESSION] Error clearing unvoted comparisons: {e}")


def unvoted_comparisons(session: str) -> int:
    try:
        counter = get_redis_client().get(REDIS_UNVOTED_KEY.format(session=session))
        assert not isinstance(counter, Awaitable)
        return int(counter) if counter else 0
    except Exception as e:
        logger.error(f"[SESSION] Error reading unvoted comparisons: {e}")
        return 0
