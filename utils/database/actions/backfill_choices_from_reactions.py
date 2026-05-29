import logging
import uuid
from collections import defaultdict

from sqlalchemy import text, update

from utils.database.models.turn import Turn
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

BATCH_SIZE = 10_000

_QUERY_BASE = f"""
    SELECT
        conversation_pair_id, model_pos, msg_rank,
        liked, disliked,
        useful, complete, creative, clear_formatting,
        incorrect, superficial, instructions_not_followed
    FROM reactions
    WHERE {NOT_ARCHIVED}
"""

QUERY = _QUERY_BASE
QUERY_FILTERED = _QUERY_BASE + "    AND conversation_pair_id = ANY(:ids)"

POSITIVE_FLAGS = ("liked", "useful", "complete", "creative", "clear_formatting")
NEGATIVE_FLAGS = ("disliked", "incorrect", "superficial", "instructions_not_followed")


def _side_sentiment(flags: set[str]) -> str:
    has_pos = any(f in POSITIVE_FLAGS for f in flags)
    has_neg = any(f in NEGATIVE_FLAGS for f in flags)
    if has_pos and not has_neg:
        return "good"
    if has_neg and not has_pos:
        return "bad"
    return "neutral"


def _derive_choice(flags_a: set[str], flags_b: set[str]) -> str | None:
    s_a = _side_sentiment(flags_a)
    s_b = _side_sentiment(flags_b)

    if s_a == s_b == "good":
        return "both_good"
    if s_a == s_b == "bad":
        return "both_bad"
    if s_a == "good" or s_b == "bad":
        return "a_better"
    if s_b == "good" or s_a == "bad":
        return "b_better"
    return None


async def backfill_choices_from_reactions(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
) -> None:
    """
    Backfill turn.choice for turns that have no choice but whose source reactions
    allow deriving a preference. Works per (pair_id, msg_rank) so a 3-turn
    conversation with reactions on 3 turns produces 3 choices, not 1.

    Only updates turns where choice IS NULL. Skips when sentiment is neutral/mixed.

    Requires: turn_map.pkl
    """
    ensure_maps_dir(maps_dir)

    turn_map: dict[tuple[str, int, int], uuid.UUID] = load_map(maps_dir, "turn_map")

    pair_occurrences: dict[str, set[int]] = defaultdict(set)
    for (pair_id, occ, _turn_idx) in turn_map:
        pair_occurrences[pair_id].add(occ)

    # Accumulate flags per (pair_id, msg_rank, model_pos)
    # flags[(pair_id, msg_rank, side)] = set of active flags
    flags: dict[tuple[str, int, str], set[str]] = defaultdict(set)

    with source_connection(source_uri, stream=True) as conn:
        result = conn.execute(text(QUERY))
        while True:
            rows = result.mappings().fetchmany(BATCH_SIZE)
            if not rows:
                break
            for row in rows:
                pair_id = row["conversation_pair_id"]
                side = row["model_pos"]
                msg_rank = row["msg_rank"]
                if not pair_id or side not in ("a", "b") or msg_rank is None:
                    continue
                key = (pair_id, int(msg_rank), side)
                for flag in POSITIVE_FLAGS + NEGATIVE_FLAGS:
                    if row.get(flag):
                        flags[key].add(flag)

    # Group by (pair_id, msg_rank) and derive choice per turn
    turn_choices: dict[tuple[str, int], str] = {}
    turn_keys = {(pair_id, rank) for (pair_id, rank, _side) in flags}

    for pair_id, rank in turn_keys:
        choice = _derive_choice(
            flags.get((pair_id, rank, "a"), set()),
            flags.get((pair_id, rank, "b"), set()),
        )
        if choice is not None:
            turn_choices[(pair_id, rank)] = choice

    logger.info(f"{len(turn_choices)} (pair_id, msg_rank) resolved, {len(turn_keys) - len(turn_choices)} skipped (neutral/mixed).")

    # Map to turn_ids via turn_map
    updates: list[dict] = []
    unmapped = 0

    for (pair_id, rank), choice in turn_choices.items():
        occs = pair_occurrences.get(pair_id)
        if not occs:
            unmapped += 1
            continue
        for occ in occs:
            turn_id = turn_map.get((pair_id, occ, rank))
            if turn_id is None:
                unmapped += 1
                continue
            updates.append({"turn_id": turn_id, "choice": choice})

    logger.info(f"{len(updates)} turns to update, {unmapped} unmapped.")

    if not updates:
        return

    if not commit:
        logger.info("Dry run: no changes written.")
        return

    for batch_start in range(0, len(updates), BATCH_SIZE):
        batch = updates[batch_start : batch_start + BATCH_SIZE]
        async with get_session() as session:
            for u in batch:
                await session.execute(
                    update(Turn)
                    .where(Turn.id == u["turn_id"])
                    .where(Turn.choice == None)
                    .values(choice=u["choice"])
                )
            await session.commit()
        logger.info(f"Batch {batch_start // BATCH_SIZE}: {len(batch)} turns updated.")

    logger.info(f"Done: {len(updates)} turns updated.")
