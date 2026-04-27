"""
Arena session management for conversation state in Redis.

Handles storing and retrieving conversation pairs during active arena sessions.
"""

import json
import logging
from typing import Awaitable, TypedDict
from uuid import uuid4

from backend.config import (
    RATELIMIT_CUSTOM_SELECTION_PER_DAY,
    RATELIMIT_CUSTOM_SELECTION_PER_HOUR,
    RATELIMIT_PRICEY_MODELS_INPUT,
)
from utils.storage.redis import (
    REDIS_CONVERSATIONS_KEY,
    REDIS_CUSTOM_DAILY_KEY,
    REDIS_CUSTOM_HOURLY_KEY,
    REDIS_USER_CHAR_COUNT,
    get_redis_client,
)

logger = logging.getLogger("languia")


class ComparisonMetadata(TypedDict):
    id: int
    session_hash: str
    is_streaming: bool


def create_session() -> str:
    """
    Generate a new unique session hash.

    Returns:
        str: UUID-based session identifier
    """
    return str(uuid4())


def store_comparison_metadata(session_hash: str, id: int, is_streaming: bool) -> None:
    expire_time = 86400  # 24 hours

    try:
        client = get_redis_client()
        client.setex(
            REDIS_CONVERSATIONS_KEY.format(session_hash=session_hash),
            expire_time,
            json.dumps(
                {"id": id, "session_hash": session_hash, "is_streaming": is_streaming}
            ),
        )
        logger.info(f"[SESSION] Stored conversations for {session_hash}")
    except Exception as e:
        logger.error(f"[SESSION] Error storing session: {e}")
        raise


def retreive_comparison_metadata(
    session_hash: str,
) -> ComparisonMetadata:
    try:
        client = get_redis_client()
        data = client.get(REDIS_CONVERSATIONS_KEY.format(session_hash=session_hash))
        assert not isinstance(data, Awaitable)
        if not data:
            logger.warning(f"[SESSION] Session not found: {session_hash}")
            raise ValueError(f"Session not found: {session_hash}")

        logger.info(f"[SESSION] Retrieved conversations for {session_hash}")

        return json.loads(data)

    except json.JSONDecodeError as e:
        logger.error(f"[SESSION] Error decoding session data: {e}")
        raise ValueError(f"Invalid session data for {session_hash}")
    except Exception as e:
        logger.error(f"[SESSION] Error retrieving session: {e}")
        raise


# FIXME unused?
def delete_session(session_hash: str) -> bool:
    """
    Delete a session from Redis.

    Args:
        session_hash: Unique session identifier

    Returns:
        bool: True if session was deleted, False if it didn't exist
    """
    try:
        client = get_redis_client()
        deleted = client.delete(
            REDIS_CONVERSATIONS_KEY.format(session_hash=session_hash)
        )
        logger.info(f"[SESSION] Deleted session {session_hash}: {bool(deleted)}")
        return bool(deleted)
    except Exception as e:
        logger.error(f"[SESSION] Error deleting session: {e}")
        return False


def increment_input_chars(ip: str, input_chars: int) -> None:
    """
    Track input character count per IP address for rate limiting.

    Increments a counter in Redis for the given IP and sets expiry to 2 hours.
    This prevents users from overloading expensive model APIs.

    Args:
        ip: User's IP address
        input_chars: Number of input characters to add to counter

    Returns:
        bool: False if Redis not configured, True otherwise
    """
    client = get_redis_client()
    # Increment counter under key "ip:{ip}"
    client.incrby(REDIS_USER_CHAR_COUNT.format(ip=ip), input_chars)
    # Set counter to expire in 2 hours (3600 * 2 seconds)
    client.expire(REDIS_USER_CHAR_COUNT.format(ip=ip), 3600 * 2)


def increment_custom_selections(ip: str) -> None:
    """
    Track custom model selection count per IP address for rate limiting.

    Increments two Redis counters: hourly (1h expiry) and daily (24h expiry).

    Args:
        ip: User's IP address
    """
    client = get_redis_client()
    client.incr(REDIS_CUSTOM_HOURLY_KEY.format(ip=ip))
    client.expire(REDIS_CUSTOM_HOURLY_KEY.format(ip=ip), 3600)
    client.incr(REDIS_CUSTOM_DAILY_KEY.format(ip=ip))
    client.expire(REDIS_CUSTOM_DAILY_KEY.format(ip=ip), 86400)


def is_custom_selection_ratelimited(ip: str) -> bool:
    """
    Check if an IP address has exceeded rate limit for custom model selections.

    Checks both hourly and daily limits.

    Args:
        ip: User's IP address

    Returns:
        bool: True if either hourly or daily limit is exceeded
    """
    client = get_redis_client()
    hourly = client.get(REDIS_CUSTOM_HOURLY_KEY.format(ip=ip))
    assert not isinstance(hourly, Awaitable)
    if hourly and int(hourly) >= RATELIMIT_CUSTOM_SELECTION_PER_HOUR:
        return True
    daily = client.get(REDIS_CUSTOM_DAILY_KEY.format(ip=ip))
    assert not isinstance(daily, Awaitable)
    if daily and int(daily) >= RATELIMIT_CUSTOM_SELECTION_PER_DAY:
        return True
    return False


def is_ratelimited(ip: str) -> bool:
    """
    Check if an IP address has exceeded rate limit for expensive models.

    Args:
        ip: User's IP address

    Returns:
        bool: True if IP has exceeded limit (2x RATELIMIT_PRICEY_MODELS_INPUT), False otherwise
    """
    client = get_redis_client()
    counter = client.get(REDIS_USER_CHAR_COUNT.format(ip=ip))
    assert not isinstance(counter, Awaitable)
    # Rate limit is 2x the configured limit for pricey models
    if counter and int(counter) > RATELIMIT_PRICEY_MODELS_INPUT * 2:
        return True
    else:
        return False
