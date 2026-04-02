import logging
from datetime import datetime

from sqlalchemy import text

from utils.utils import db_connection

from ..utils import TABLE_NAMES, archive

logger = logging.getLogger("comparia.database")

# TODO those could be repared
CORRUPTED_CONVERSATIONS_QUERY = """
    SELECT 
        conversation_pair_id
    FROM 
        conversations
    WHERE
        archived IS NULL
        AND (
            conversation_a::text LIKE '%%ModelResponseStream%%'
            OR conversation_b::text LIKE '%%ModelResponseStream%%'
        )
    ;
"""

CORRUPTED_REACTIONS_QUERY = """
    SELECT 
        id,
        conversation_pair_id,
        conversation_a,
        conversation_b,
        msg_index,
        msg_rank,
        chatbot_index
    FROM 
        reactions
    WHERE
        archived IS NULL
        -- Filter potentially incoherent data
        AND (
            -- 1. msg_index referencing a conversation must be within conversation bounds
            msg_index >= GREATEST(
                jsonb_array_length(conversation_a),
                jsonb_array_length(conversation_b)
            )
            -- 2. Message at reacted to (at msg_index) must be from assistant role
            -- Check in refers_to_conv_id (which is either conv_a_id or conv_b_id)
            OR (
                CASE
                    WHEN refers_to_conv_id = conv_a_id THEN
                        (conversation_a->msg_index->>'role' != 'assistant')
                    WHEN refers_to_conv_id = conv_b_id THEN
                        (conversation_b->msg_index->>'role' != 'assistant')
                    ELSE FALSE
                END
            )
        )
    ;
"""

# TODO:
# check conv a & b len is same? check system_msg
# + cf https://github.com/betagouv/ComparIA/issues/285


def archive_corrupted(*, commit: bool = False) -> None:
    """
    Archive conversations, votes and reaction with corrupted data.
    """
    logger.info("Searching for corrupted conversations")

    archived_at = datetime.now()
    with db_connection(stream=True) as conn:
        conv_results = conn.execute(text(CORRUPTED_CONVERSATIONS_QUERY)).all()
        ids = [result[0] for result in conv_results]

    if not ids:
        logger.info("No corrupted conversations found!")
    else:
        logger.warning(f"Found {len(ids)} 'conversations' with corrupted content.")

        for table_name in TABLE_NAMES:
            # archive corrupted 'conversations' and related 'votes' + 'reactions'
            archive(table_name, ids, "corrupted", archived_at, commit=commit)

    logger.info("Searching for corrupted reactions")

    with db_connection(stream=True) as conn:
        reactions_results = conn.execute(text(CORRUPTED_REACTIONS_QUERY)).all()
        ids = [result[0] for result in reactions_results]

    if not ids:
        logger.info("No corrupted reactions found!")
    else:
        logger.warning(f"Found {len(ids)} 'reactions' with corrupted content.")

        archive("reactions", ids, "corrupted", archived_at, id_key="id", commit=commit)
