import logging
import uuid
from datetime import datetime, timedelta

import tiktoken
from sqlalchemy import text

_enc = tiktoken.get_encoding("cl100k_base")

from utils.database.models.messages.llm import LLMMessage
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, save_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

QUERY = f"""
    SELECT conversation_pair_id, timestamp, conversation_a, conversation_b
    FROM conversations
    WHERE {NOT_ARCHIVED}
"""

BATCH_SIZE = 10_000


UNKNOWN_GENERATION_ID = "unknown"


def _build_llm_message(msg: dict, fallback_ts: datetime) -> LLMMessage | None:
    content = msg.get("content")
    if not content:
        return None

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
        generation_id=str(generation_id) if generation_id is not None else UNKNOWN_GENERATION_ID,
        tokens=int(tokens) if tokens is not None else len(_enc.encode(str(content))),
        is_cached=bool(metadata.get("is_cached", False)),
        created_at=fallback_ts,
        responded_at=fallback_ts,
        updated_at=updated_at,
        reasoning_content=None,
    )


def _extract_assistant_messages(conversation: list[dict] | None) -> list[tuple[int, dict]]:
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
) -> None:
    """
    Step 3: migrate JSONB conversation messages → llm_message table.

    Requires: comparison_map.pkl
    Produces: llm_message_map.pkl ((pair_id, side, turn_idx) → llm_message uuid)
    Rows with NULL generation_id or tokens are skipped.
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[str, uuid.UUID] = load_map(maps_dir, "comparison_map")
    llm_message_map: dict[tuple[str, str, int], uuid.UUID] = {}

    inserted = 0
    skipped = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
        result = conn.execute(text(QUERY))
        while True:
            raw_rows = result.mappings().fetchmany(BATCH_SIZE)
            if not raw_rows:
                break

            to_insert: list[LLMMessage] = []
            batch_map: dict[tuple[str, str, int], uuid.UUID] = {}

            batch_skipped = 0
            for row in raw_rows:
                pair_id: str | None = row["conversation_pair_id"]
                if not pair_id or pair_id not in comparison_map:
                    batch_skipped += 1
                    continue

                ts: datetime = row["timestamp"]

                for side, conversation in [("a", row["conversation_a"]), ("b", row["conversation_b"])]:
                    for turn_idx, msg in _extract_assistant_messages(conversation):
                        llm_msg = _build_llm_message(msg, ts)
                        if llm_msg is None:
                            logger.debug(
                                f"Skipping llm_message ({pair_id}, {side}, {turn_idx}): {msg}"
                            )
                            batch_skipped += 1
                            continue
                        to_insert.append(llm_msg)
                        batch_map[(pair_id, side, turn_idx)] = llm_msg.id

            if commit and to_insert:
                async with get_session() as session:
                    session.add_all(to_insert)
                    await session.commit()

            llm_message_map.update(batch_map)
            inserted += len(to_insert)
            skipped += batch_skipped
            logger.info(f"Batch {batch_idx}: {len(to_insert)} inserted, {batch_skipped} skipped.")
            batch_idx += 1

    logger.info(f"Done: {inserted} inserted, {skipped} skipped.")
    save_map(maps_dir, "llm_message_map", llm_message_map)
