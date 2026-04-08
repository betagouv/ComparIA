import logging
from datetime import datetime
from typing import Literal, Sequence, get_args

from sqlalchemy import text

from utils.utils import db_connection

TableName = Literal["conversations", "votes", "reactions"]
TABLE_NAMES: tuple[TableName, ...] = get_args(TableName)

ArchivedReason = Literal[
    "corrupted_model_stream",
    "corrupted_against_self",
    "corrupted_no_model",
    "corrupted_out_of_range_reactions",
    "corrupted_to_model_msg_reactions",
    "corrupted_no_choice_votes",
    "duplicate",
    "duplicate_has_vote",
    "spam",
    "unknown_llm",
    "unknown",
]

logger = logging.getLogger("comparia.database")


def archive(
    table_name: TableName,
    ids: Sequence[str | int],
    archived_reason: ArchivedReason,
    archived_at: datetime,
    id_key: str = "conversation_pair_id",
    commit: bool = False,
) -> int:
    """
    Archive given table related ids objects with reason and archive date.
    Log only by default what would have been archive, set 'commit' to True to
    actually archive those.
    """
    query = """
        UPDATE {table_name} 
        SET 
            archived = TRUE,
            archived_reason = '{archived_reason}',
            archived_at = '{archived_at}'
        WHERE
            {id_key} IN ({ids});
    """.format(
        table_name=table_name,
        archived_reason=archived_reason,
        archived_at=archived_at,
        ids=", ".join([f"'{id}'" for id in ids]),
        id_key=id_key,
    )

    with db_connection() as conn:
        results = conn.execute(text(query))

        if commit:
            conn.commit()
            logger.info(
                f"Successfully archived {results.rowcount} '{archived_reason}' {table_name}."
            )
        else:
            logger.error(
                f"{results.rowcount} '{archived_reason}' {table_name} should be archived."
            )

        return results.rowcount


def reset_archived():
    """
    Reset all conversations, votes and reaction 'archived' column to NULL if FALSE.
    Used to run db linting in hard mode (reanalyzing).
    """
    query = """
        UPDATE
            {table_name}
        SET
            archived = NULL
        WHERE
            archived = FALSE
        ;
    """
    with db_connection() as conn:
        for table_name in TABLE_NAMES:
            logger.info(
                f"Resetting 'achived=FALSE' to 'archived=NULL' in {table_name}."
            )
            results = conn.execute(text(query.format(table_name=table_name)))

            conn.commit()
            logger.info(
                f"Resetted {results.rowcount} 'archived' to NULL on {table_name}."
            )


def set_not_archived(timestamp: datetime):
    """
    Set all conversations, votes and reaction 'archived' column to FALSE if NULL.
    Only affects items inserted before given timestamp.
    Used after linting to mark data as analyzed.
    """
    query = """
        UPDATE {table_name} 
        SET archived = FALSE
        WHERE archived IS NULL AND timestamp < TIMESTAMP '{timestamp}';
    """

    with db_connection() as conn:
        for table_name in TABLE_NAMES:
            logger.info(
                f"Set {table_name} 'archived' to FALSE if timestamp < {timestamp}."
            )
            results = conn.execute(
                text(query.format(table_name=table_name, timestamp=timestamp))
            )

            conn.commit()
            logger.info(f"Set {results.rowcount} 'archived' to FALSE on {table_name}.")
