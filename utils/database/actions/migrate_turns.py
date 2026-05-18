import logging
import uuid
from datetime import datetime

import polars as pl
from sqlalchemy import insert as sa_insert
from sqlalchemy import text, update

from utils.database.models.messages.user import UserMessage
from utils.database.models.turn import Turn
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, save_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

QUERY = f"""
    SELECT conversation_pair_id, timestamp, conversation_a
    FROM conversations
    WHERE {NOT_ARCHIVED}
"""

BATCH_SIZE = 10_000


def _count_turns(conversation: list[dict] | None) -> int:
    if not conversation:
        return 0
    count = 0
    for msg in conversation:
        if msg.get("role") == "user":
            count += 1
    return count


async def migrate_turns(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
) -> None:
    """
    Step 5: create turn rows linking comparison, user_message, llm_msg_a, llm_msg_b.
    Also backfills user_message.turn_id for each inserted turn.

    Requires: comparison_map.pkl, llm_message_map.pkl, user_message_map.pkl
    Produces: turn_map.pkl ((pair_id, turn_idx) → turn uuid)
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[str, uuid.UUID] = load_map(maps_dir, "comparison_map")
    llm_message_map: dict[tuple[str, str, int], uuid.UUID] = load_map(maps_dir, "llm_message_map")
    user_message_map: dict[tuple[str, int], uuid.UUID] = load_map(maps_dir, "user_message_map")

    turn_map: dict[tuple[str, int], uuid.UUID] = {}

    inserted = 0
    skipped = 0

    with source_connection(source_uri, stream=True) as conn:
        batches = pl.read_database(
            query=text(QUERY), connection=conn, iter_batches=True, batch_size=BATCH_SIZE
        )
        for batch_idx, batch in enumerate(batches):
            turns_to_insert: list[dict] = []
            user_msg_backfill: list[tuple[uuid.UUID, uuid.UUID]] = []
            batch_map: dict[tuple[str, int], uuid.UUID] = {}

            for row in batch.iter_rows(named=True):
                pair_id: str | None = row["conversation_pair_id"]
                if not pair_id or pair_id not in comparison_map:
                    skipped += 1
                    continue

                comparison_id = comparison_map[pair_id]
                ts: datetime = row["timestamp"]
                n_turns = _count_turns(row["conversation_a"])

                for turn_idx in range(n_turns):
                    user_msg_id = user_message_map.get((pair_id, turn_idx))
                    llm_msg_a_id = llm_message_map.get((pair_id, "a", turn_idx))
                    llm_msg_b_id = llm_message_map.get((pair_id, "b", turn_idx))

                    if user_msg_id is None:
                        logger.debug(f"No user_message for ({pair_id}, {turn_idx}), skipping turn.")
                        skipped += 1
                        continue

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
                    user_msg_backfill.append((user_msg_id, turn_id))
                    batch_map[(pair_id, turn_idx)] = turn_id

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

    logger.info(f"Done: {inserted} inserted, {skipped} skipped.")
    save_map(maps_dir, "turn_map", turn_map)
