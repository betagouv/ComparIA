"""
Arena session management for conversation state in Redis.

Handles storing and retrieving conversation pairs during active arena sessions.
"""

import json
import logging
from typing import Tuple
from uuid import uuid4

import redis

from backend.config import settings

logger = logging.getLogger("languia")

try:
    redis_host = settings.COMPARIA_REDIS_HOST
    r = redis.Redis(host=redis_host, port=6379, decode_responses=True)
    response = r.ping()
    if not response:
        logger.error(f"Redis connection error - {response}")
except Exception as e:
    raise Exception(f"Redis Connection Error: {e}")


def create_session() -> str:
    """
    Generate a new unique session hash.

    Returns:
        str: UUID-based session identifier
    """
    return str(uuid4())


def store_session_conversations(session_hash: str, data: dict) -> None:
    """
    Store conversation pair with metadata in Redis for an active session.

    Args:
        session_hash: Unique session identifier
        data: serialized conversations data (see Conversations.store_to_session)

    Note:
        Session expires after 24 hours
    """
    from datetime import datetime

    expire_time = 86400  # 24 hours

    try:
        r.setex(f"session:{session_hash}", expire_time, json.dumps(data))
        logger.info(f"[SESSION] Stored conversations for {session_hash}")
    except Exception as e:
        logger.error(f"[SESSION] Error storing session: {e}")
        raise


def retrieve_session_conversations(
    session_hash: str,
) -> dict:
    """
    Retrieve conversation pair and metadata from Redis.

    Args:
        session_hash: Unique session identifier

    Returns:
        Tuple[dict, dict, dict]: (conv_a, conv_b, metadata)
            where metadata contains {"mode": str, "category": str, "created_at": str}

    Raises:
        ValueError: If session not found or expired
    """
    try:
        data = r.get(f"session:{session_hash}")
        if not data:
            logger.warning(f"[SESSION] Session not found: {session_hash}")
            raise ValueError(f"Session not found: {session_hash}")

        # parsed = json.loads(data)
        logger.info(f"[SESSION] Retrieved conversations for {session_hash}")

        return json.loads(data)

    except json.JSONDecodeError as e:
        logger.error(f"[SESSION] Error decoding session data: {e}")
        raise ValueError(f"Invalid session data for {session_hash}")
    except Exception as e:
        logger.error(f"[SESSION] Error retrieving session: {e}")
        raise


def update_session_conversations(
    session_hash: str,
    conv_a: dict,
    conv_b: dict,
    mode: str | None = None,
    category: str | None = None,
) -> None:
    """
    Update existing session conversations and metadata.

    Args:
        session_hash: Unique session identifier
        conv_a: Updated first conversation state
        conv_b: Updated second conversation state
        mode: Model selection mode (optional, preserves existing if None)
        category: Prompt category (optional, preserves existing if None)
    """
    # If mode/category not provided, preserve existing values
    if mode is None or category is None:
        try:
            _, _, existing_metadata = retrieve_session_conversations(session_hash)
            mode = mode or existing_metadata.get("mode")
            category = category or existing_metadata.get("category")
        except ValueError:
            # Session doesn't exist yet, use provided values
            pass

    store_session_conversations(session_hash, conv_a, conv_b, mode, category)


def delete_session(session_hash: str) -> bool:
    """
    Delete a session from Redis.

    Args:
        session_hash: Unique session identifier

    Returns:
        bool: True if session was deleted, False if it didn't exist
    """
    try:
        deleted = r.delete(f"session:{session_hash}")
        logger.info(f"[SESSION] Deleted session {session_hash}: {bool(deleted)}")
        return bool(deleted)
    except Exception as e:
        logger.error(f"[SESSION] Error deleting session: {e}")
        return False


def increment_input_chars(ip: str, input_chars: int) -> bool:
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
    if not redis_host:
        return False
    # Increment counter under key "ip:{ip}"
    r.incrby(f"ip:{ip}", input_chars)
    # Set counter to expire in 2 hours (3600 * 2 seconds)


def is_ratelimited(ip: str) -> bool:
    """
    Check if an IP address has exceeded rate limit for expensive models.

    Args:
        ip: User's IP address

    Returns:
        bool: True if IP has exceeded limit (2x RATELIMIT_PRICEY_MODELS_INPUT), False otherwise
    """
    counter = r.get(f"ip:{ip}")
    # Rate limit is 2x the configured limit for pricey models
    if counter and int(counter) > RATELIMIT_PRICEY_MODELS_INPUT * 2:
        return True
    else:
        return False
