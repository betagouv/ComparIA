import logging
import uuid

import polars as pl
from sqlalchemy import text, update

from utils.database.models.turn import Turn
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, bool_flags_to_keywords, ensure_maps_dir, load_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

QUERY = f"""
    SELECT
        v.conversation_pair_id,
        v.chosen_model_name, v.both_equal,
        v.conv_comments_a, v.conv_comments_b,
        v.conv_useful_a, v.conv_useful_b,
        v.conv_complete_a, v.conv_complete_b,
        v.conv_creative_a, v.conv_creative_b,
        v.conv_clear_formatting_a, v.conv_clear_formatting_b,
        v.conv_incorrect_a, v.conv_incorrect_b,
        v.conv_superficial_a, v.conv_superficial_b,
        v.conv_instructions_not_followed_a, v.conv_instructions_not_followed_b,
        c.model_a_name, c.model_b_name
    FROM votes v
    JOIN conversations c ON v.conversation_pair_id = c.conversation_pair_id
    WHERE v.{NOT_ARCHIVED}
"""

POSITIVE_COLS = ["useful", "complete", "creative", "clear_formatting"]
NEGATIVE_COLS = ["incorrect", "superficial", "instructions_not_followed"]

BATCH_SIZE = 10_000


def _derive_choice(row: dict) -> str:
    if row.get("both_equal"):
        return "both_good"
    chosen = row.get("chosen_model_name")
    if chosen and chosen == row.get("model_a_name"):
        return "a_better"
    if chosen and chosen == row.get("model_b_name"):
        return "b_better"
    return "idk"


def _build_keywords(row: dict, side: str) -> list[str]:
    cols = [f"conv_{col}_{side}" for col in POSITIVE_COLS + NEGATIVE_COLS]
    return [col.removeprefix(f"conv_").removesuffix(f"_{side}") for col in cols if row.get(col)]


async def migrate_votes(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
) -> None:
    """
    Step 6: migrate votes → update last turn of each comparison with choice and keyword annotations.

    Requires: comparison_map.pkl, turn_map.pkl
    """
    ensure_maps_dir(maps_dir)

    comparison_map: dict[str, uuid.UUID] = load_map(maps_dir, "comparison_map")
    turn_map: dict[tuple[str, int], uuid.UUID] = load_map(maps_dir, "turn_map")

    # Precompute last turn per pair_id
    last_turn: dict[str, tuple[int, uuid.UUID]] = {}
    for (pair_id, turn_idx), turn_id in turn_map.items():
        if pair_id not in last_turn or turn_idx > last_turn[pair_id][0]:
            last_turn[pair_id] = (turn_idx, turn_id)

    updated = 0
    skipped = 0

    with source_connection(source_uri, stream=True) as conn:
        batches = pl.read_database(
            query=text(QUERY), connection=conn, iter_batches=True, batch_size=BATCH_SIZE
        )
        for batch_idx, batch in enumerate(batches):
            updates: list[dict] = []

            for row in batch.iter_rows(named=True):
                pair_id: str | None = row["conversation_pair_id"]
                if not pair_id or pair_id not in comparison_map or pair_id not in last_turn:
                    skipped += 1
                    continue

                _, turn_id = last_turn[pair_id]
                choice = _derive_choice(row)
                kw_a = _build_keywords(row, "a")
                kw_b = _build_keywords(row, "b")

                updates.append(
                    {
                        "turn_id": turn_id,
                        "choice": choice,
                        "keyword_annotations_a": kw_a,
                        "keyword_annotations_b": kw_b,
                        "custom_annotation_a": row.get("conv_comments_a"),
                        "custom_annotation_b": row.get("conv_comments_b"),
                    }
                )

            if commit and updates:
                async with get_session() as session:
                    for u in updates:
                        await session.execute(
                            update(Turn)
                            .where(Turn.id == u["turn_id"])
                            .values(
                                choice=u["choice"],
                                keyword_annotations_a=u["keyword_annotations_a"],
                                keyword_annotations_b=u["keyword_annotations_b"],
                                custom_annotation_a=u["custom_annotation_a"],
                                custom_annotation_b=u["custom_annotation_b"],
                            )
                        )
                    await session.commit()

            updated += len(updates)
            logger.info(f"Batch {batch_idx}: {len(updates)} turns updated.")

    logger.info(f"Done: {updated} turns updated, {skipped} votes skipped.")
