import logging
import uuid
from collections import defaultdict

from sqlalchemy import text

from utils.database.session import get_session

from .migrate_utils import ensure_maps_dir, load_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

_QUERY_SELECT = "SELECT conversation_pair_id, timestamp, conversation_a, conversation_b FROM conversations"

BATCH_SIZE = 10_000


def _extract_reasoning(conversation: list[dict] | None) -> list[tuple[int, str | None]]:
    """Returns (turn_index, reasoning_content) for assistant messages."""
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
                rc = assistant_msg.get("reasoning_content") or None
                result.append((turn_idx, rc))
                turn_idx += 1
                i += 2
                continue
        i += 1
    return result


async def migrate_reasoning_content(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Backfill step: update llm_message.reasoning_content from source conversation JSONB.

    Requires: llm_message_map.pkl
    When incremental=True, only processes pair_ids in new_pair_ids.pkl.
    Only updates rows where reasoning_content IS NULL and source has a non-empty value.
    """
    ensure_maps_dir(maps_dir)

    llm_message_map: dict[tuple[str, int, str, int], uuid.UUID] = load_map(
        maps_dir, "llm_message_map"
    )

    # Group pair_ids to query
    pair_ids_in_map: set[str] = {
        pair_id for (pair_id, _occ, _side, _turn_idx) in llm_message_map
    }

    if incremental:
        new_pair_ids: set[str] = load_map(maps_dir, "new_pair_ids")
        if not new_pair_ids:
            logger.info("No new pair_ids to process.")
            return
        pair_ids_to_process = pair_ids_in_map & new_pair_ids
    else:
        pair_ids_to_process = pair_ids_in_map

    logger.info(
        f"Processing {len(pair_ids_to_process)} pair_ids for reasoning_content backfill."
    )

    # Build lookup: pair_id → list of occurrences (sorted)
    pair_occ_map: dict[str, list[int]] = defaultdict(set)
    for pair_id, occ, _side, _turn_idx in llm_message_map:
        if pair_id in pair_ids_to_process:
            pair_occ_map[pair_id].add(occ)
    pair_occ_map = {k: sorted(v) for k, v in pair_occ_map.items()}

    # pair_id_counter to track occurrence index (same logic as other migrate steps)
    pair_id_counter: defaultdict[str, int] = defaultdict(int)

    # Collect updates: llm_message_id → reasoning_content
    updates: dict[uuid.UUID, str] = {}

    pair_ids_list = list(pair_ids_to_process)

    with source_connection(source_uri, stream=True) as conn:
        for batch_start in range(0, len(pair_ids_list), BATCH_SIZE):
            batch_ids = pair_ids_list[batch_start : batch_start + BATCH_SIZE]
            rows = (
                conn.execute(
                    text(
                        _QUERY_SELECT
                        + " WHERE conversation_pair_id = ANY(:ids) ORDER BY conversation_pair_id, timestamp"
                    ),
                    {"ids": batch_ids},
                )
                .mappings()
                .fetchall()
            )

            for row in rows:
                pair_id: str | None = row["conversation_pair_id"]
                if not pair_id or pair_id not in pair_ids_to_process:
                    continue

                occ = pair_id_counter[pair_id]
                pair_id_counter[pair_id] += 1

                for side, conversation in [
                    ("a", row["conversation_a"]),
                    ("b", row["conversation_b"]),
                ]:
                    for turn_idx, rc in _extract_reasoning(conversation):
                        if not rc:
                            continue
                        msg_id = llm_message_map.get((pair_id, occ, side, turn_idx))
                        if msg_id is not None:
                            updates[msg_id] = rc

    logger.info(
        f"Found {len(updates)} llm_messages with reasoning_content to backfill."
    )

    if not updates:
        logger.info("Nothing to update.")
        return

    if commit:
        batch_idx = 0
        items = list(updates.items())
        for batch_start in range(0, len(items), BATCH_SIZE):
            batch = items[batch_start : batch_start + BATCH_SIZE]
            async with get_session() as session:
                for msg_id, rc in batch:
                    await session.execute(
                        text("""
                            UPDATE llm_message
                            SET reasoning_content = :rc
                            WHERE id = :id AND reasoning_content IS NULL
                        """),
                        {"rc": rc, "id": msg_id},
                    )
                await session.commit()
            logger.info(f"Batch {batch_idx}: {len(batch)} rows updated.")
            batch_idx += 1
        logger.info(f"Done: {len(updates)} llm_messages updated.")
    else:
        logger.info(f"Dry run: would update {len(updates)} llm_messages.")
