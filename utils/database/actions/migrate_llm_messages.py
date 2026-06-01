import logging
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

import tiktoken
from sqlalchemy import text

_enc = tiktoken.get_encoding("cl100k_base")

from utils.database.models.messages.llm import LLMMessage
from utils.database.session import get_session

from .migrate_utils import (
    ensure_maps_dir,
    load_map,
    load_map_or_empty,
    save_map,
    source_connection,
)

logger = logging.getLogger("comparia.db.migrate")

_QUERY_SELECT = "SELECT conversation_pair_id, timestamp, conversation_a, conversation_b FROM conversations"
QUERY = _QUERY_SELECT + " ORDER BY conversation_pair_id, timestamp"

BATCH_SIZE = 10_000


UNKNOWN_GENERATION_ID = "unknown"


def _build_llm_message(msg: dict, fallback_ts: datetime) -> LLMMessage | None:
    content = msg.get("content") or ""

    metadata = msg.get("metadata") or {}
    generation_id = metadata.get("generation_id")
    tokens = metadata.get("output_tokens")

    duration = metadata.get("duration")
    updated_at = (
        fallback_ts + timedelta(milliseconds=duration)
        if duration is not None
        else fallback_ts
    )

    return LLMMessage(
        id=uuid.uuid4(),
        content=str(content),
        generation_id=(
            str(generation_id) if generation_id is not None else UNKNOWN_GENERATION_ID
        ),
        tokens=int(tokens) if tokens is not None else len(_enc.encode(str(content))),
        is_cached=bool(metadata.get("is_cached", False)),
        created_at=fallback_ts,
        responded_at=fallback_ts,
        updated_at=updated_at,
        reasoning_content=None,
    )


def _extract_assistant_messages(
    conversation: list[dict] | None,
) -> list[tuple[int, dict]]:
    if not conversation:
        return []
    result = []
    turn_idx = 0
    i = 0
    while i < len(conversation):
        if conversation[i].get("role") == "system":
            i += 1
            continue
        if conversation[i].get("role") == "user" and i + 1 < len(conversation):
            assistant_msg = conversation[i + 1]
            if assistant_msg.get("role") == "assistant":
                result.append((turn_idx, assistant_msg))
                turn_idx += 1
                i += 2
                continue
        i += 1
    return result


async def migrate_llm_messages(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Step 3: migrate JSONB conversation messages → llm_message table.

    Requires: comparison_map.pkl
    Produces: llm_message_map.pkl ((pair_id, side, turn_idx) → llm_message uuid)
    Rows with NULL generation_id or tokens are skipped.
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[tuple[str, int], uuid.UUID] = load_map(
        maps_dir, "comparison_map"
    )
    existing_llm_message_map: dict[tuple[str, int, str, int], uuid.UUID] = (
        load_map_or_empty(maps_dir, "llm_message_map") if incremental else {}
    )
    llm_message_map: dict[tuple[str, int, str, int], uuid.UUID] = dict(
        existing_llm_message_map
    )
    pair_id_counter: dict[str, int] = defaultdict(int)

    inserted = 0
    skipped_no_pair_id = 0
    skipped_not_in_map = 0
    skipped_no_msg = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
        if incremental:
            new_pair_ids: set[str] = load_map(maps_dir, "new_pair_ids")
            if not new_pair_ids:
                logger.info("No new pair_ids to process.")
                save_map(maps_dir, "llm_message_map", llm_message_map)
                return
            result = conn.execute(
                text(
                    _QUERY_SELECT
                    + " WHERE conversation_pair_id = ANY(:ids) ORDER BY conversation_pair_id, timestamp"
                ),
                {"ids": list(new_pair_ids)},
            )
        else:
            result = conn.execute(text(QUERY))
        while True:
            raw_rows = result.mappings().fetchmany(BATCH_SIZE)
            if not raw_rows:
                break

            to_insert: list[LLMMessage] = []
            batch_map: dict[tuple[str, int, str, int], uuid.UUID] = {}

            batch_no_pair_id = 0
            batch_not_in_map = 0
            batch_no_msg = 0
            for row in raw_rows:
                pair_id: str | None = row["conversation_pair_id"]
                if not pair_id:
                    batch_no_pair_id += 1
                    continue
                occ = pair_id_counter[pair_id]
                pair_id_counter[pair_id] += 1
                if (pair_id, occ) not in comparison_map:
                    batch_not_in_map += 1
                    continue

                ts: datetime = row["timestamp"]

                for side, conversation in [
                    ("a", row["conversation_a"]),
                    ("b", row["conversation_b"]),
                ]:
                    for turn_idx, msg in _extract_assistant_messages(conversation):
                        llm_msg = _build_llm_message(msg, ts)
                        if llm_msg is None:
                            batch_no_msg += 1
                            continue
                        to_insert.append(llm_msg)
                        batch_map[(pair_id, occ, side, turn_idx)] = llm_msg.id

            if commit and to_insert:
                async with get_session() as session:
                    session.add_all(to_insert)
                    await session.commit()

            llm_message_map.update(batch_map)
            inserted += len(to_insert)
            skipped_no_pair_id += batch_no_pair_id
            skipped_not_in_map += batch_not_in_map
            skipped_no_msg += batch_no_msg
            batch_skipped = batch_no_pair_id + batch_not_in_map + batch_no_msg
            logger.info(
                f"Batch {batch_idx}: {len(to_insert)} inserted, {batch_skipped} skipped"
                f" (no_pair_id={batch_no_pair_id}, not_in_map={batch_not_in_map}, no_msg={batch_no_msg})."
            )
            batch_idx += 1

    total_skipped = skipped_no_pair_id + skipped_not_in_map + skipped_no_msg
    logger.info(
        f"Done: {inserted} inserted, {total_skipped} skipped"
        f" (no_pair_id={skipped_no_pair_id}, not_in_map={skipped_not_in_map}, no_msg={skipped_no_msg})."
    )
    save_map(
        maps_dir, "llm_message_map", llm_message_map
    )  # key: (pair_id, occ, side, turn_idx)
