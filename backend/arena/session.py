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


def store_session_conversations(
    session_hash: str, conv_a: dict, conv_b: dict
) -> None:
    """
    Store conversation pair in Redis for an active session.

    Args:
        session_hash: Unique session identifier
        conv_a: First conversation state (dict with messages, model_name, etc.)
        conv_b: Second conversation state (dict with messages, model_name, etc.)

    Note:
        Session expires after 24 hours
    """
    data = {"conv_a": conv_a, "conv_b": conv_b}
    expire_time = 86400  # 24 hours

    try:
        r.setex(f"session:{session_hash}", expire_time, json.dumps(data))
        logger.info(f"[SESSION] Stored conversations for {session_hash}")
    except Exception as e:
        logger.error(f"[SESSION] Error storing session: {e}")
        raise


def retrieve_session_conversations(session_hash: str) -> Tuple[dict, dict]:
    """
    Retrieve conversation pair from Redis.

    Args:
        session_hash: Unique session identifier

    Returns:
        Tuple[dict, dict]: (conv_a, conv_b) conversation states

    Raises:
        ValueError: If session not found or expired
    """
    try:
        data = r.get(f"session:{session_hash}")
        if not data:
            logger.warning(f"[SESSION] Session not found: {session_hash}")
            raise ValueError(f"Session not found: {session_hash}")

        parsed = json.loads(data)
        logger.info(f"[SESSION] Retrieved conversations for {session_hash}")
        return (parsed["conv_a"], parsed["conv_b"])

    except json.JSONDecodeError as e:
        logger.error(f"[SESSION] Error decoding session data: {e}")
        raise ValueError(f"Invalid session data for {session_hash}")
    except Exception as e:
        logger.error(f"[SESSION] Error retrieving session: {e}")
        raise


def update_session_conversations(
    session_hash: str, conv_a: dict, conv_b: dict
) -> None:
    """
    Update existing session conversations (alias for store_session_conversations).

    Args:
        session_hash: Unique session identifier
        conv_a: Updated first conversation state
        conv_b: Updated second conversation state
    """
    store_session_conversations(session_hash, conv_a, conv_b)


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
