"""
Database queries for fetching tool arena vote data for ranking computation.

Uses psycopg2 with RealDictCursor, matching the existing pattern
from utils/ranking/queries.py.
"""

import logging

from psycopg2.extras import RealDictCursor

from utils.storage.db import db_cursor
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.tool_queries"))


def fetch_tool_votes() -> list[dict]:
    """
    Fetch all tool arena votes for ranking computation.

    Returns:
        List of dicts with keys: tool_a_id, tool_b_id, chosen,
        session_hash, task, goal, timestamp.
    """
    with db_cursor("get tool votes", logger, cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            "SELECT tool_a_id, tool_b_id, chosen, session_hash, task, goal, timestamp"
            " FROM tool_votes"
        )
        return [dict(row) for row in cursor.fetchall()]

    return []
