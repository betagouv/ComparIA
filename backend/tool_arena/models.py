"""
Data models for CompaRAG Tool Arena.

Defines all data structures for:
- MCPToolCall: runtime model for a single MCP tool invocation
- ToolCallRecord: DB-ready serialization model (mirrors VoteRecord pattern)
- save_tool_call_to_db: persists a tool call to the tool_calls table
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Annotated, Any, Iterator
from uuid import uuid4

import psycopg2
from pydantic import BaseModel, Field, PlainSerializer

from backend.config import settings  # ONLY for COMPARIA_DB_URI

logger = logging.getLogger("tool_arena")


class MCPToolCall(BaseModel):
    """
    Represents a single MCP tool invocation within the tool arena.

    Stores everything needed for blind comparison and vote attribution.
    Completely isolated from the LLM arena Conversation model.
    """

    call_id: str = Field(default_factory=lambda: str(uuid4()).replace("-", ""))
    session_id: str
    task: str
    goal: str
    tool_id: str  # references mcp_servers.json key
    llm_id: str  # litellm model name used to mediate the result
    raw_result: str  # raw MCP server response (supports DATA-03 sanitization traceability)
    mediated_result: str  # LLM-processed output shown to user
    duration_ms: int
    created_at: Annotated[datetime, PlainSerializer(lambda v: v.isoformat())] = Field(
        default_factory=datetime.now
    )
    error: str | None = None  # captures failure reason if any


class ToolCallRecord(BaseModel):
    """
    DB serialization model for MCPToolCall (mirrors VoteRecord pattern).

    All fields are flat primitive types ready for parameterized INSERT.
    No default_factory — this is constructed from a completed MCPToolCall.
    """

    call_id: str
    session_id: str
    task: str
    goal: str
    tool_id: str
    llm_id: str
    raw_result: str
    mediated_result: str
    duration_ms: int
    created_at: str  # ISO format string (not datetime), matching VoteRecord timestamp pattern
    error: str | None = None


@contextmanager
def db(
    data: dict,
    action: str,
) -> Iterator[tuple[Any, str, str]]:
    """
    Local copy of the db() context manager pattern from backend/arena/persistence.py.
    Yields cursor and parameterized field/value strings for INSERT queries.

    Args:
        data: Pydantic model dump to be passed to the query
        action: String like "save 'tool_call'" describing the operation for logging

    Yields:
        Tuple of (cursor, field_keys, value_keys) for use in INSERT statements

    Raises:
        psycopg2.Error: If database operation fails
    """
    try:
        logger.debug(f"[DB] Try to {action} data")

        with psycopg2.connect(settings.COMPARIA_DB_URI) as conn:
            with conn.cursor() as cursor:
                data_keys = list(data.keys())
                field_keys = ", ".join(data_keys)
                value_keys = ", ".join(f"%({k})s" for k in data_keys)
                yield (cursor, field_keys, value_keys)

    except psycopg2.Error as e:
        logger.error(f"[DB] Error couldn't {action} data: {e}", exc_info=True)


def save_tool_call_to_db(data: dict) -> dict:
    """
    Save a tool call record to the tool_calls table.

    Args:
        data: ToolCallRecord.model_dump(mode='json') with all flat fields

    Returns:
        dict: The saved data dict

    Raises:
        psycopg2.Error: If database operation fails
    """
    with db(data, "save 'tool_call'") as (cursor, fields, values):
        insert_statement = psycopg2.sql.SQL(f"""
            INSERT INTO tool_calls ({fields})
            VALUES ({values})
        """)

        cursor.execute(insert_statement, data)

    logger.info(f"[DB] Saved tool_call {data['call_id']} for session {data['session_id']}")

    return data
