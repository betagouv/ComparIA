import logging
import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import insert as sa_insert
from sqlalchemy import text

from utils.database.models.comparison import Comparison
from utils.database.session import get_session

from .migrate_utils import (
    ensure_maps_dir,
    load_map,
    load_map_or_empty,
    save_map,
    source_connection,
)

logger = logging.getLogger("comparia.db.migrate")

_QUERY_SELECT = """
    SELECT
        conversation_pair_id, timestamp,
        session_hash, ip, visitor_id, cohorts, mode, custom_models_selection,
        model_a_name, model_b_name,
        system_prompt_a, system_prompt_b,
        pii_analyzed, contains_pii, contains_spam,
        short_summary, keywords, categories, languages,
        archived, archived_reason, archived_at
    FROM conversations
"""

QUERY = _QUERY_SELECT + "    ORDER BY conversation_pair_id, timestamp"

VALID_MODES = {"random", "big-vs-small", "small-models", "custom"}
BATCH_SIZE = 10_000


async def migrate_comparisons(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
    incremental: bool = False,
) -> None:
    """
    Step 2: migrate conversations → comparison table.

    Requires: system_message_map.pkl
    Produces: comparison_map.pkl (conversation_pair_id → comparison uuid)

    When incremental=True, loads existing comparison_map, processes only new pair_ids,
    and saves new_pair_ids.pkl for use by subsequent incremental steps.
    """
    ensure_maps_dir(maps_dir)

    system_map: dict[str, uuid.UUID] = load_map(maps_dir, "system_message_map")

    existing_comparison_map: dict[tuple[str, int], uuid.UUID] = (
        load_map_or_empty(maps_dir, "comparison_map") if incremental else {}
    )
    comparison_map: dict[tuple[str, int], uuid.UUID] = dict(existing_comparison_map)
    pair_id_counter: dict[str, int] = defaultdict(int)

    inserted = 0
    skipped = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
        if incremental:
            existing_pair_ids = {p for p, _ in existing_comparison_map}
            if existing_pair_ids:
                new_ids_result = conn.execute(
                    text(
                        "SELECT DISTINCT conversation_pair_id FROM conversations"
                        " WHERE conversation_pair_id IS NOT NULL"
                        " AND conversation_pair_id != ALL(:ids)"
                    ),
                    {"ids": list(existing_pair_ids)},
                )
            else:
                new_ids_result = conn.execute(
                    text(
                        "SELECT DISTINCT conversation_pair_id FROM conversations"
                        " WHERE conversation_pair_id IS NOT NULL"
                    )
                )
            new_pair_ids: set[str] = {row[0] for row in new_ids_result.fetchall()}
            save_map(maps_dir, "new_pair_ids", new_pair_ids)
            if not new_pair_ids:
                logger.info("No new pair_ids to migrate.")
                save_map(maps_dir, "comparison_map", comparison_map)
                return
            logger.info(f"Incremental: {len(new_pair_ids)} new pair_ids to process.")
            result = conn.execute(
                text(
                    _QUERY_SELECT
                    + "    WHERE conversation_pair_id = ANY(:ids)"
                    + "    ORDER BY conversation_pair_id, timestamp"
                ),
                {"ids": list(new_pair_ids)},
            )
        else:
            result = conn.execute(text(QUERY))
        while True:
            raw_rows = result.mappings().fetchmany(BATCH_SIZE)
            if not raw_rows:
                break

            rows_to_insert: list[dict] = []

            for row in raw_rows:
                pair_id = row["conversation_pair_id"]
                if not pair_id:
                    skipped += 1
                    continue

                occ = pair_id_counter[pair_id]
                pair_id_counter[pair_id] += 1
                if occ > 0:
                    logger.debug(
                        f"Duplicate pair_id={pair_id} (occurrence {occ}), inserting as new comparison."
                    )

                ts: datetime = row["timestamp"]
                mode = row["mode"] if row["mode"] in VALID_MODES else "random"
                system_prompt_a = row["system_prompt_a"] or ""
                system_prompt_b = row["system_prompt_b"] or ""

                comp_id = uuid.uuid4()
                rows_to_insert.append(
                    {
                        "id": comp_id,
                        "created_at": ts,
                        "updated_at": ts,
                        "session_hash": row["session_hash"] or "",
                        "ip": row["ip"] or "",
                        "visitor_id": row["visitor_id"],
                        "cohorts": row["cohorts"],
                        "mode": mode,
                        "custom_models_selection": row["custom_models_selection"],
                        "llm_id_a": row["model_a_name"] or "",
                        "llm_id_b": row["model_b_name"] or "",
                        "system_msg_a_id": (
                            system_map.get(system_prompt_a) if system_prompt_a else None
                        ),
                        "system_msg_b_id": (
                            system_map.get(system_prompt_b) if system_prompt_b else None
                        ),
                        "llm_analyzed": row["pii_analyzed"],
                        "contains_pii": row["contains_pii"],
                        "contains_spam": row["contains_spam"],
                        "short_summary": row["short_summary"],
                        "keywords": row["keywords"],
                        "categories": row["categories"],
                        "languages": row["languages"],
                        "archived": row["archived"],
                        "archived_reason": row["archived_reason"],
                        "archived_at": row["archived_at"],
                        "error": None,
                    }
                )
                comparison_map[(pair_id, occ)] = comp_id

            if commit and rows_to_insert:
                async with get_session() as session:
                    await session.execute(sa_insert(Comparison), rows_to_insert)
                    await session.commit()

            inserted += len(rows_to_insert)
            logger.info(
                f"Batch {batch_idx}: {len(rows_to_insert)} comparisons processed."
            )
            batch_idx += 1

    logger.info(f"Done: {inserted} inserted, {skipped} skipped.")
    save_map(maps_dir, "comparison_map", comparison_map)
