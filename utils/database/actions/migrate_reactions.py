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
        conversation_pair_id, model_pos, msg_rank,
        liked, disliked, useful, complete, creative, clear_formatting,
        incorrect, superficial, instructions_not_followed,
        comment
    FROM reactions
    WHERE {NOT_ARCHIVED}
"""

QUERY = _QUERY_BASE
QUERY_FILTERED = _QUERY_BASE + "    AND conversation_pair_id = ANY(:ids)"

REACTION_FLAGS = [
    "useful",
    "complete",
    "creative",
    "clear_formatting",
    "incorrect",
    "superficial",
    "instructions_not_followed",
]

BATCH_SIZE = 10_000


async def migrate_reactions(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Step 7: migrate reactions → update turn keyword_annotations and custom_annotation.
    Uses msg_rank as turn index.
    Merge strategy: union (no duplicates). custom_annotation only set if not already present.

    Requires: comparison_map.pkl, turn_map.pkl
    """
    ensure_maps_dir(maps_dir)

    turn_map: dict[tuple[str, int, int], uuid.UUID] = load_map(maps_dir, "turn_map")

    pair_occurrences: dict[str, set[int]] = defaultdict(set)
    for pair_id, occ, _turn_idx in turn_map:
        pair_occurrences[pair_id].add(occ)

    pending: dict[uuid.UUID, dict] = defaultdict(
        lambda: {"kw_a": set(), "kw_b": set(), "custom_a": None, "custom_b": None}
    )

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

            for row in raw_rows:
                pair_id: str | None = row["conversation_pair_id"]
                msg_rank = row["msg_rank"]
                model_pos: str | None = row["model_pos"]

                if not pair_id or msg_rank is None or model_pos not in ("a", "b"):
                    skipped += 1
                    continue

                occs = pair_occurrences.get(pair_id)
                if not occs:
                    skipped += 1
                    continue

                rank = int(msg_rank)
                kw_key = f"kw_{model_pos}"
                custom_key = f"custom_{model_pos}"
                comment = row.get("comment")
                active_flags = [flag for flag in REACTION_FLAGS if row.get(flag)]

                matched = False
                for occ in occs:
                    turn_id = turn_map.get((pair_id, occ, rank))
                    if turn_id is None:
                        continue
                    matched = True
                    for flag in active_flags:
                        pending[turn_id][kw_key].add(flag)
                    if comment and pending[turn_id][custom_key] is None:
                        pending[turn_id][custom_key] = comment

                if not matched:
                    logger.debug(
                        f"No turn for ({pair_id}, msg_rank={msg_rank}), skipping."
                    )
                    skipped += 1

            logger.info(f"Batch {batch_idx}: accumulated reactions.")
            batch_idx += 1

    logger.info(
        f"Accumulated {len(pending)} turns to update, {skipped} reactions skipped."
    )

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
