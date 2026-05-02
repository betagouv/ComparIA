"""
Tool arena session management for comparison state in Redis.

Handles creating, storing, and retrieving tool arena sessions during blind comparison.
Completely isolated from backend.arena session management.
"""

import json
from uuid import uuid4

from utils.storage.redis import get_redis_client

TOOL_ARENA_SESSION_KEY = "tool_arena:{session_hash}"


def create_tool_session() -> str:
    """
    Generate a new unique session hash for a tool arena comparison.

    Returns:
        str: UUID-based session identifier (with dashes)
    """
    return str(uuid4())


def store_tool_session(session_hash: str, data: dict) -> None:
    """
    Store tool arena comparison state in Redis with 24h expiry.

    Args:
        session_hash: Unique session identifier
        data: Session state dict (task, goal, llm_id_a/b, voted flag, tool_a/b MCPToolCall dicts)

    Note:
        Session expires after 24 hours (86400 seconds) per D-07.
    """
    client = get_redis_client()
    client.setex(
        TOOL_ARENA_SESSION_KEY.format(session_hash=session_hash),
        86400,  # 24 hours per D-07
        json.dumps(data),
    )


def retrieve_tool_session(session_hash: str) -> dict:
    """
    Retrieve tool arena comparison state from Redis.

    Args:
        session_hash: Unique session identifier

    Returns:
        dict: Session state with task, goal, llm_id_a/b, voted, tool_a, tool_b

    Raises:
        ValueError: If session not found or expired
    """
    client = get_redis_client()
    raw = client.get(TOOL_ARENA_SESSION_KEY.format(session_hash=session_hash))
    if not raw:
        raise ValueError(f"Tool arena session not found: {session_hash}")
    return json.loads(raw)
