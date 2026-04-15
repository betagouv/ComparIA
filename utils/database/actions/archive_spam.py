import logging
from datetime import datetime
from typing import TYPE_CHECKING

import polars as pl
from sqlalchemy import text

from backend.arena.spam_detection import is_spam
from utils.utils import db_connection

from ..utils import TABLE_NAMES, archive

if TYPE_CHECKING:
    pass

logger = logging.getLogger("comparia.db")

QUERY = """
    SELECT 
        conversation_pair_id,
        conversation_a,
        conversation_b
    FROM 
        conversations
    WHERE
        archived IS NULL
    ;
"""


def conversation_contains_spam(conversation: list[dict]) -> bool:
    """
    Check if a conversation (JSONB field) contains spam in user messages.

    Args:
        conversation: list of messages

    Returns:
        True if any user message contains spam, False otherwise
    """
    for message in conversation:
        if message["role"] == "user" and is_spam(message["content"]):
            return True

    return False


def archive_spam(*, commit: bool = False) -> None:
    """
    Archive conversations, votes and reactions for which we find spam in conversations.
    """
    logger.info("Searching for spam in conversations.")

    ids: list[str] = []
    with db_connection(stream=True) as conn:
        result_chunks = pl.read_database(
            query=text(QUERY), connection=conn, iter_batches=True, batch_size=10_000
        )
        for index, results in enumerate(result_chunks):
            logger.debug(f"Process batch {index} of {len(results)} rows.")

            for row in results.iter_rows(named=True):
                if conversation_contains_spam(
                    row["conversation_a"]
                ) or conversation_contains_spam(row["conversation_b"]):
                    ids.append(row["conversation_pair_id"])

    if not ids:
        logger.info(f"No conversations with spam found!")
        return

    logger.warning(f"Found {len(ids)} conversations with spam.")
    archived_at = datetime.now()

    for table_name in TABLE_NAMES:
        archive(table_name, ids, "spam", archived_at, commit=commit)
