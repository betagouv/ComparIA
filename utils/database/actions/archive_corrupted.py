import logging
from collections import defaultdict
from datetime import datetime
from typing import Literal, cast

import polars as pl
from sqlalchemy import text

from utils.utils import db_connection

from ..models.comparison import ArchivedReason
from ..utils import TABLE_NAMES, archive

logger = logging.getLogger("comparia.db")


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
    msgs_b = [msg for msg in conv_b if msg["role"] != "system"]
    if len(msgs_a) != len(msgs_b):
        return True
    return False


def archive_corrupted(*, commit: bool = False) -> None:
    """
    Archive comparisons with corrupted data.
    """
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
                        continue

                    nonish_contents = [
                        has_nonish_content(msgs) for msgs in assistant_msgs.values()
                    ]
                    if nonish := next((n for n in nonish_contents if n), None):
                        reason = cast(
                            ArchivedReason,
                            f"corrupted_response_{nonish[0]}_{nonish[1]}",
                        )
                        reasons[reason].add(_id)
                        continue

                    if any(
                        has_model_stream_content(msgs)
                        for msgs in assistant_msgs.values()
                    ):
                        reasons["corrupted_model_stream"].add(_id)
                    elif not_equal_length(row["conversation_a"], row["conversation_b"]):
                        reasons["corrupted_not_equal_length"].add(_id)

    for reason, ids in reasons.items():
        logger.warning(
            f"Found {len(ids)} conversations with corrupted content: '{reason}'."
        )
        for tb in TABLE_NAMES:
            # archive corrupted 'conversations' and related 'votes' + 'reactions'
            archive(tb, list(ids), reason, archived_at, commit=commit)
