import logging
from collections import defaultdict
from datetime import datetime
from typing import Literal, cast

import polars as pl
from sqlalchemy import text

from utils.utils import db_connection

from ..utils import TABLE_NAMES, ArchivedReason, TableName, archive

logger = logging.getLogger("comparia.db")


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


def has_nonish_content(
    msgs: list,
) -> tuple[Literal["all", "last", "some"], Literal["none", "empty"]] | None:
    count = len(msgs)
    are_none = [msg.get("content") is None for msg in msgs]
    are_empty = [msg.get("content") == "" for msg in msgs]
    kinds: dict[Literal["none", "empty"], list[bool]] = {
        "none": [msg.get("content") is None for msg in msgs],
        "empty": [msg.get("content") == "" for msg in msgs],
    }
    for k, nonishs in kinds.items():
        n = len([nonish for nonish in nonishs if nonish is True])
        if n == 0:
            continue
        if n == count:
            return ("all", k)
        if nonishs.index(True) == count - 1:
            return ("last", k)
        return ("some", k)

    return None


def has_model_stream_content(msgs: list) -> bool:
    contents = [msg.get("content", "") for msg in msgs]
    return any(
        content.startswith("ModelResponse") or "ModelResponseStream" in content
        for content in contents
    )


def not_equal_length(conv_a: list, conv_b: list) -> bool:
    msgs_a = [msg for msg in conv_a if msg["role"] != "system"]
    msgs_b = [msg for msg in conv_a if msg["role"] != "system"]
    if len(msgs_a) != len(msgs_b):
        return True
    return False


def archive_corrupted_conversations(*, commit: bool = False) -> None:
    query = """
        SELECT 
            conversation_pair_id,
            model_a_name,
            model_b_name,
            conversation_a,
            conversation_b
        FROM 
            conversations
        WHERE
            archived IS NULL
    """
    logger.info("Searching for corrupted data in conversations")
    archived_at = datetime.now()
    reasons: dict[ArchivedReason, set[str]] = defaultdict(lambda: set())

    with db_connection(stream=True) as conn:
        result_chunks = pl.read_database(
            query=text(query), connection=conn, iter_batches=True, batch_size=10_000
        )
        for index, results in enumerate(result_chunks):
            logger.debug(f"Process batch {index} of {len(results)} conversations.")
            for row in results.iter_rows(named=True):
                _id = row["conversation_pair_id"]
                if row["model_a_name"] is None or row["model_b_name"] is None:
                    reasons["corrupted_no_model"].add(_id)
                elif row["model_a_name"] == row["model_b_name"]:
                    reasons["corrupted_against_self"].add(_id)
                else:
                    assistant_msgs = {
                        k: [
                            msg
                            for msg in row[f"conversation_{k}"]
                            if msg["role"] == "assistant"
                        ]
                        for k in ("a", "b")
                    }

                    if any(len(msgs) == 0 for msgs in assistant_msgs.values()):
                        reasons["corrupted_no_response"].add(_id)
                    elif nonish := next(
                        has_nonish_content(msgs) for msgs in assistant_msgs.values()
                    ):
                        reason = cast(
                            ArchivedReason,
                            f"corrupted_response_{nonish[0]}_{nonish[1]}",
                        )
                        reasons[reason].add(_id)
                    elif next(
                        has_model_stream_content(msgs)
                        for msgs in assistant_msgs.values()
                    ):
                        reasons["corrupted_model_stream"].add(_id)
                    elif not_equal_length(row["conversation_a"], row["conversation_a"]):
                        reasons["corrupted_not_equal_length"].add(_id)

    for reason, ids in reasons.items():
        logger.warning(
            f"Found {len(ids)} conversations with corrupted content: '{reason}'."
        )
        for tb in TABLE_NAMES:
            # archive corrupted 'conversations' and related 'votes' + 'reactions'
            archive(tb, list(ids), reason, archived_at, commit=commit)


def archive_corrupted(*, commit: bool = False) -> None:
    """
    Archive conversations, votes and reaction with corrupted data.
    """
    logger.info("Searching for corrupted data")
    archive_corrupted_conversations(commit=commit)

    archived_at = datetime.now()
    queries: dict[TableName, dict[ArchivedReason, str]] = {
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

                archive(
                    table_name, ids, reason, archived_at, id_key="id", commit=commit
                )
