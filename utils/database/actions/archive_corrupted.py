import logging
from datetime import datetime

from sqlalchemy import text

from utils.utils import db_connection

from ..utils import TABLE_NAMES, ArchivedReason, TableName, archive

logger = logging.getLogger("comparia.database")

# TODO those could be repared
CORRUPTED_MODEL_STREAM_CONVERSATIONS_QUERY = """
    SELECT conversation_pair_id FROM conversations
    WHERE
        archived IS NULL
        AND (
            conversation_a::text LIKE '%%ModelResponseStream%%'
            OR conversation_b::text LIKE '%%ModelResponseStream%%'
        )
    ;
"""
CORRUPTED_AGAINST_SELF_CONVERSATIONS_QUERY = """
    SELECT conversation_pair_id FROM conversations
    WHERE
        archived IS NULL
        AND model_a_name = model_b_name
    ;
"""
CORRUPTED_NO_MODEL_CONVERSATIONS_QUERY = """
    SELECT conversation_pair_id FROM conversations
    WHERE
        archived IS NULL
        AND (
            model_a_name IS NULL 
            OR model_b_name IS NULL
        )
    ;
"""

CORRUPTED_NO_CHOICE_VOTES_QUERY = """
    SELECT id FROM votes
    WHERE
        archived IS NULL
        -- votes with neither chosen model nor is both_equal
        AND (
            chosen_model_name IS NULL 
            AND (both_equal = FALSE OR both_equal IS NULL)
        )
"""

CORRUPTED_OUT_OF_RANGE_INDEX_REACTIONS_QUERY = """
    SELECT id FROM reactions
    WHERE
        archived IS NULL
        -- msg_index referencing a conversation is out of range
        AND msg_index >= GREATEST(
            jsonb_array_length(conversation_a),
            jsonb_array_length(conversation_b)
        )
    ;
"""
CORRUPTED_TO_MODEL_MSG_REACTIONS_QUERY = """
    SELECT id FROM reactions
    WHERE
        archived IS NULL
        -- Message at reacted to (at msg_index) must be from assistant role
        -- Check in refers_to_conv_id (which is either conv_a_id or conv_b_id)
        AND CASE
            WHEN refers_to_conv_id = conv_a_id THEN
                (conversation_a->msg_index->>'role' != 'assistant')
            WHEN refers_to_conv_id = conv_b_id THEN
                (conversation_b->msg_index->>'role' != 'assistant')
            ELSE FALSE
        END
    ;
"""

# TODO:
# check conv a & b len is same? check system_msg
# + cf https://github.com/betagouv/ComparIA/issues/285


def archive_corrupted(*, commit: bool = False) -> None:
    """
    Archive conversations, votes and reaction with corrupted data.
    """
    archived_at = datetime.now()
    logger.info("Searching for corrupted data")
    queries: dict[TableName, dict[ArchivedReason, str]] = {
        "conversations": {
            "corrupted_model_stream": CORRUPTED_MODEL_STREAM_CONVERSATIONS_QUERY,
            "corrupted_against_self": CORRUPTED_AGAINST_SELF_CONVERSATIONS_QUERY,
            "corrupted_no_model": CORRUPTED_NO_MODEL_CONVERSATIONS_QUERY,
        },
        "reactions": {
            "corrupted_out_of_range_reactions": CORRUPTED_OUT_OF_RANGE_INDEX_REACTIONS_QUERY,
            "corrupted_to_model_msg_reactions": CORRUPTED_TO_MODEL_MSG_REACTIONS_QUERY,
        },
        "votes": {"corrupted_no_choice_votes": CORRUPTED_NO_CHOICE_VOTES_QUERY},
    }

    for table_name, qs in queries.items():
        logger.info(f"Searching for corrupted {table_name}")

        for reason, query in qs.items():
            with db_connection(stream=True) as conn:
                conv_results = conn.execute(text(query)).all()
                ids = [result[0] for result in conv_results]

            if not ids:
                logger.info(f"No '{reason}' {table_name} found!")
            else:
                logger.warning(
                    f"Found {len(ids)} {table_name} with corrupted content: '{reason}'."
                )

                if table_name == "conversations":
                    for tb in TABLE_NAMES:
                        # archive corrupted 'conversations' and related 'votes' + 'reactions'
                        archive(tb, ids, reason, archived_at, commit=commit)
                else:
                    archive(
                        table_name, ids, reason, archived_at, id_key="id", commit=commit
                    )
