import logging
import uuid
from collections import defaultdict

from sqlalchemy import text, update

from utils.database.models.turn import Turn
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

_QUERY_BASE = f"""
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

QUERY = _QUERY_BASE
QUERY_FILTERED = _QUERY_BASE + "    AND v.conversation_pair_id = ANY(:ids)"

ANNOTATION_COLS = [
    "useful", "complete", "creative", "clear_formatting",
    "incorrect", "superficial", "instructions_not_followed",
]

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
    return [col for col in ANNOTATION_COLS if row.get(f"conv_{col}_{side}")]


async def migrate_votes(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Step 6: migrate votes → update last turn of each comparison with choice and keyword annotations.

    Requires: comparison_map.pkl, turn_map.pkl
    """
    ensure_maps_dir(maps_dir)

    turn_map: dict[tuple[str, int, int], uuid.UUID] = load_map(maps_dir, "turn_map")

    # Build per-(pair_id, occ) last turn index
    pair_occurrences: dict[str, set[int]] = defaultdict(set)
    last_turn: dict[tuple[str, int], tuple[int, uuid.UUID]] = {}
    for (pair_id, occ, turn_idx), turn_id in turn_map.items():
        pair_occurrences[pair_id].add(occ)
        key = (pair_id, occ)
        if key not in last_turn or turn_idx > last_turn[key][0]:
            last_turn[key] = (turn_idx, turn_id)

    updated = 0
    skipped = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
        if incremental:
            new_pair_ids: set[str] = load_map(maps_dir, "new_pair_ids")
            if not new_pair_ids:
                logger.info("No new pair_ids to process.")
                return
            result = conn.execute(text(QUERY_FILTERED), {"ids": list(new_pair_ids)})
        else:
            result = conn.execute(text(QUERY))
        while True:
            raw_rows = result.mappings().fetchmany(BATCH_SIZE)
            if not raw_rows:
                break

            updates: list[dict] = []

            for row in raw_rows:
                pair_id: str | None = row["conversation_pair_id"]
                occs = pair_occurrences.get(pair_id) if pair_id else None
                if not pair_id or not occs:
                    skipped += 1
                    continue

                choice = _derive_choice(row)
                kw_a = _build_keywords(row, "a")
                kw_b = _build_keywords(row, "b")
                custom_a = row.get("conv_comments_a")
                custom_b = row.get("conv_comments_b")

                for occ in occs:
                    lt = last_turn.get((pair_id, occ))
                    if lt is None:
                        continue
                    _, turn_id = lt
                    updates.append(
                        {
                            "turn_id": turn_id,
                            "choice": choice,
                            "keyword_annotations_a": kw_a,
                            "keyword_annotations_b": kw_b,
                            "custom_annotation_a": custom_a,
                            "custom_annotation_b": custom_b,
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
            batch_idx += 1

    logger.info(f"Done: {updated} turns updated, {skipped} votes skipped.")
