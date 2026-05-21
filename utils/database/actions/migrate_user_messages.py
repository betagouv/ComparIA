import logging
import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import text

from utils.database.models.messages.user import UserMessage
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, load_map_or_empty, save_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

_QUERY_SELECT = "SELECT conversation_pair_id, timestamp, conversation_a FROM conversations"
QUERY = _QUERY_SELECT + " ORDER BY conversation_pair_id, timestamp"

BATCH_SIZE = 10_000


def _extract_user_messages(conversation: list[dict] | None) -> list[tuple[int, str]]:
    """Returns (turn_index, content) pairs for user messages (one per turn)."""
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
            next_msg = conversation[i + 1]
            if next_msg.get("role") == "assistant":
                content = conversation[i].get("content") or ""
                result.append((turn_idx, content))
                turn_idx += 1
                i += 2
                continue
        i += 1
    return result


async def migrate_user_messages(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Step 4: migrate user messages from conversation_a JSONB → user_message table.
    One user_message per turn, shared between side a and b (same prompt).

    Requires: comparison_map.pkl
    Produces: user_message_map.pkl ((pair_id, turn_idx) → user_message uuid)
    turn_id is set to NULL here and backfilled in migrate_turns (step 5).
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[tuple[str, int], uuid.UUID] = load_map(maps_dir, "comparison_map")
    existing_user_message_map: dict[tuple[str, int, int], uuid.UUID] = (
        load_map_or_empty(maps_dir, "user_message_map") if incremental else {}
    )
    user_message_map: dict[tuple[str, int, int], uuid.UUID] = dict(existing_user_message_map)
    pair_id_counter: dict[str, int] = defaultdict(int)

    inserted = 0
    skipped = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
        if incremental:
            new_pair_ids: set[str] = load_map(maps_dir, "new_pair_ids")
            if not new_pair_ids:
                logger.info("No new pair_ids to process.")
                save_map(maps_dir, "user_message_map", user_message_map)
                return
            result = conn.execute(
                text(_QUERY_SELECT + " WHERE conversation_pair_id = ANY(:ids) ORDER BY conversation_pair_id, timestamp"),
                {"ids": list(new_pair_ids)},
            )
        else:
            result = conn.execute(text(QUERY))
        while True:
            raw_rows = result.mappings().fetchmany(BATCH_SIZE)
            if not raw_rows:
                break

            to_insert: list[UserMessage] = []
            batch_map: dict[tuple[str, int, int], uuid.UUID] = {}

            for row in raw_rows:
                pair_id: str | None = row["conversation_pair_id"]
                if not pair_id:
                    skipped += 1
                    continue
                occ = pair_id_counter[pair_id]
                pair_id_counter[pair_id] += 1
                if (pair_id, occ) not in comparison_map:
                    skipped += 1
                    continue

                ts: datetime = row["timestamp"]

                for turn_idx, content in _extract_user_messages(row["conversation_a"]):
                    msg_id = uuid.uuid4()
                    to_insert.append(UserMessage(id=msg_id, content=content, created_at=ts, turn_id=None))
                    batch_map[(pair_id, occ, turn_idx)] = msg_id

            if commit and to_insert:
                async with get_session() as session:
                    session.add_all(to_insert)
                    await session.commit()

            user_message_map.update(batch_map)
            inserted += len(to_insert)
            logger.info(f"Batch {batch_idx}: {len(to_insert)} user_messages processed.")
            batch_idx += 1

    logger.info(f"Done: {inserted} inserted, {skipped} skipped.")
    save_map(maps_dir, "user_message_map", user_message_map)  # key: (pair_id, occ, turn_idx)
