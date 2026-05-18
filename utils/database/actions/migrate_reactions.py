import logging
import uuid
from collections import defaultdict

import polars as pl
from sqlalchemy import text, update

from utils.database.models.turn import Turn
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

QUERY = f"""
    SELECT
        conversation_pair_id, model_pos, msg_rank,
        liked, disliked, useful, complete, creative, clear_formatting,
        incorrect, superficial, instructions_not_followed,
        comment
    FROM reactions
    WHERE {NOT_ARCHIVED}
"""

POSITIVE_FLAGS = ["liked", "useful", "complete", "creative", "clear_formatting"]
NEGATIVE_FLAGS = ["disliked", "incorrect", "superficial", "instructions_not_followed"]

BATCH_SIZE = 10_000


async def migrate_reactions(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
) -> None:
    """
    Step 7: migrate reactions → update turn keyword_annotations and custom_annotation.
    Uses msg_rank as turn index.
    Merge strategy: union (no duplicates). custom_annotation only set if not already present.

    Requires: comparison_map.pkl, turn_map.pkl
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[str, uuid.UUID] = load_map(maps_dir, "comparison_map")
    turn_map: dict[tuple[str, int], uuid.UUID] = load_map(maps_dir, "turn_map")

    # Accumulate all reactions per (turn_id, side) before applying
    # {turn_id: {"kw_a": set, "kw_b": set, "custom_a": str|None, "custom_b": str|None}}
    pending: dict[uuid.UUID, dict] = defaultdict(
        lambda: {"kw_a": set(), "kw_b": set(), "custom_a": None, "custom_b": None}
    )

    skipped = 0

    with source_connection(source_uri, stream=True) as conn:
        batches = pl.read_database(
            query=text(QUERY), connection=conn, iter_batches=True, batch_size=BATCH_SIZE
        )
        for batch_idx, batch in enumerate(batches):
            for row in batch.iter_rows(named=True):
                pair_id: str | None = row["conversation_pair_id"]
                msg_rank: int | None = row["msg_rank"]
                model_pos: str | None = row["model_pos"]

                if not pair_id or msg_rank is None or model_pos not in ("a", "b"):
                    skipped += 1
                    continue
                if pair_id not in comparison_map:
                    skipped += 1
                    continue

                turn_id = turn_map.get((pair_id, int(msg_rank)))
                if turn_id is None:
                    logger.debug(f"No turn for ({pair_id}, msg_rank={msg_rank}), skipping.")
                    skipped += 1
                    continue

                kw_key = f"kw_{model_pos}"
                custom_key = f"custom_{model_pos}"

                for flag in POSITIVE_FLAGS + NEGATIVE_FLAGS:
                    if row.get(flag):
                        pending[turn_id][kw_key].add(flag)

                comment = row.get("comment")
                if comment and pending[turn_id][custom_key] is None:
                    pending[turn_id][custom_key] = comment

            logger.info(f"Batch {batch_idx}: accumulated reactions.")

    logger.info(f"Accumulated {len(pending)} turns to update, {skipped} reactions skipped.")

    if commit and pending:
        async with get_session() as session:
            for turn_id, data in pending.items():
                await session.execute(
                    update(Turn)
                    .where(Turn.id == turn_id)
                    .values(
                        keyword_annotations_a=list(data["kw_a"]),
                        keyword_annotations_b=list(data["kw_b"]),
                        custom_annotation_a=data["custom_a"],
                        custom_annotation_b=data["custom_b"],
                    )
                )
            await session.commit()
        logger.info(f"Updated {len(pending)} turns with reaction annotations.")
    elif not commit:
        logger.info(f"Dry run: would update {len(pending)} turns.")
