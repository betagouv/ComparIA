"""
Database persistence for tool arena votes.

Stores blind comparison votes in the tool_votes table.
Isolated from backend.arena — uses the local db() context manager from models.py.
"""

from pydantic import BaseModel

from backend.tool_arena.models import db  # reuse local db() context manager


class ToolVoteRecord(BaseModel):
    """
    DB serialization model for a tool arena vote.

    All fields are flat primitive types ready for parameterized INSERT.
    Matches the tool_votes table columns exactly (per D-19/D-20).
    """

    session_hash: str
    tool_a_id: str
    tool_b_id: str
    chosen: str          # "a" | "b" | "tie"
    llm_id: str
    task: str
    goal: str
    timestamp: str       # ISO format


def save_tool_vote_to_db(data: dict) -> dict:
    """
    Save a tool arena vote to the tool_votes table.

    Args:
        data: ToolVoteRecord.model_dump(mode='json') with all flat fields

    Returns:
        dict: The saved data dict

    Raises:
        psycopg2.Error: If database operation fails
    """
    with db(data, "save 'tool_vote'") as (cursor, fields, values):
        cursor.execute(
            f"INSERT INTO tool_votes ({fields}) VALUES ({values})",
            data,
        )
    return data
