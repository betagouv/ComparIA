import logging
from datetime import datetime
from typing import Literal, Sequence, get_args

from sqlalchemy import text

from utils.utils import db_connection

TableName = Literal["conversations", "votes", "reactions"]
TABLE_NAMES: tuple[TableName, ...] = get_args(TableName)

ArchivedReason = Literal[
    "corrupted_no_model",  # some Conversations model_(a|b)_name is None
    "corrupted_against_self",  # some Conversations model_a_name and model_b_name are equal
    "corrupted_no_response",  # some Conversations conversation_(a|b) has no AssistantMessage at all
    "corrupted_response_all_none",  # some Conversations conversation_(a|b) has all its AssistantMessage.content as None
    "corrupted_response_last_none",  # some Conversations conversation_(a|b) has its last AssistantMessage.content as None
    "corrupted_response_some_none",  # some Conversations conversation_(a|b) has at least one AssistantMessage.content as None
    "corrupted_response_all_empty",  # some Conversations conversation_(a|b) has all its AssistantMessage.content as ''
    "corrupted_response_last_empty",  # some Conversations conversation_(a|b) has its last AssistantMessage.content as ''
    "corrupted_response_some_empty",  # some Conversations conversation_(a|b) has at least one AssistantMessage.content as ''
    "corrupted_model_stream",  # some Conversations conversation_(a|b) has at least one AssistantMessage.content with ModelResponse or ModelResponseStream in it
    "corrupted_not_equal_length",  # Conversations conversation_(a&b) lengths are not equal (excluding SystemMessage)
    "corrupted_out_of_range_reactions",
    "corrupted_to_model_msg_reactions",
    "corrupted_no_choice_votes",
    "duplicate",
    "duplicate_has_vote",
    "spam",
    "unknown_llm",
    "unknown",
]
# TODO could be fixed?
# - "corrupted_response_(last|some)_(none|empty)":
#   - remove corresponding UserMessage + AssistantMessage
#   - remove corresponding reactions
#   - if "some":
#       - update other reactions msg_index accordingly
# - "corrupted_model_stream": reparse AssistantMessage content

logger = logging.getLogger("comparia.db")


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
