import logging
import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import insert as sa_insert
from sqlalchemy import text, update

from utils.database.models.messages.user import UserMessage
from utils.database.models.turn import Turn
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, load_map_or_empty, save_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

_QUERY_SELECT = "SELECT conversation_pair_id, timestamp, conversation_a FROM conversations"
QUERY = _QUERY_SELECT + " ORDER BY conversation_pair_id, timestamp"

BATCH_SIZE = 10_000


def _count_turns(conversation: list[dict] | None) -> int:
    if not conversation:
        return 0
    count = 0
    i = 0
    while i < len(conversation):
        if conversation[i].get("role") == "system":
            i += 1
            continue
        if conversation[i].get("role") == "user" and i + 1 < len(conversation):
            if conversation[i + 1].get("role") == "assistant":
                count += 1
                i += 2
                continue
        i += 1
    return count


async def migrate_turns(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Step 5: create turn rows linking comparison, user_message, llm_msg_a, llm_msg_b.
    Also backfills user_message.turn_id for each inserted turn.

    Requires: comparison_map.pkl, llm_message_map.pkl, user_message_map.pkl
    Produces: turn_map.pkl ((pair_id, turn_idx) → turn uuid)
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[tuple[str, int], uuid.UUID] = load_map(maps_dir, "comparison_map")
    llm_message_map: dict[tuple[str, int, str, int], uuid.UUID] = load_map(maps_dir, "llm_message_map")
    user_message_map: dict[tuple[str, int, int], uuid.UUID] = load_map(maps_dir, "user_message_map")

    existing_turn_map: dict[tuple[str, int, int], uuid.UUID] = (
        load_map_or_empty(maps_dir, "turn_map") if incremental else {}
    )
    turn_map: dict[tuple[str, int, int], uuid.UUID] = dict(existing_turn_map)
    pair_id_counter: dict[str, int] = defaultdict(int)

    inserted = 0
    skipped = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
        if incremental:
            new_pair_ids: set[str] = load_map(maps_dir, "new_pair_ids")
            if not new_pair_ids:
                logger.info("No new pair_ids to process.")
                save_map(maps_dir, "turn_map", turn_map)
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

            turns_to_insert: list[dict] = []
            user_msg_backfill: list[tuple[uuid.UUID, uuid.UUID]] = []
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

                comparison_id = comparison_map[(pair_id, occ)]
                ts: datetime = row["timestamp"]
                n_turns = _count_turns(row["conversation_a"])

                for turn_idx in range(n_turns):
                    user_msg_id = user_message_map.get((pair_id, occ, turn_idx))
                    llm_msg_a_id = llm_message_map.get((pair_id, occ, "a", turn_idx))
                    llm_msg_b_id = llm_message_map.get((pair_id, occ, "b", turn_idx))

                    turn_id = uuid.uuid4()
                    turns_to_insert.append(
                        {
                            "id": turn_id,
                            "comparison_id": comparison_id,
                            "created_at": ts,
                            "updated_at": ts,
                            "choice": None,
                            "llm_msg_a_id": llm_msg_a_id,
                            "llm_msg_b_id": llm_msg_b_id,
                            "keyword_annotations_a": [],
                            "keyword_annotations_b": [],
                            "custom_annotation_a": None,
                            "custom_annotation_b": None,
                        }
                    )
                    if user_msg_id is not None:
                        user_msg_backfill.append((user_msg_id, turn_id))
                    batch_map[(pair_id, occ, turn_idx)] = turn_id

            if commit and turns_to_insert:
                async with get_session() as session:
                    await session.execute(sa_insert(Turn), turns_to_insert)
                    for user_msg_id, turn_id in user_msg_backfill:
                        await session.execute(
                            update(UserMessage)
                            .where(UserMessage.id == user_msg_id)
                            .values(turn_id=turn_id)
                        )
                    await session.commit()

            turn_map.update(batch_map)
            inserted += len(turns_to_insert)
            logger.info(f"Batch {batch_idx}: {len(turns_to_insert)} turns processed.")
            batch_idx += 1

    logger.info(f"Done: {inserted} inserted, {skipped} skipped.")
    save_map(maps_dir, "turn_map", turn_map)  # key: (pair_id, occ, turn_idx)
