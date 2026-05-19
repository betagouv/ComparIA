import logging
import uuid
from datetime import datetime

from sqlalchemy import insert as sa_insert
from sqlalchemy import text

from utils.database.models.comparison import Comparison
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, load_map, save_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

QUERY = f"""
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

VALID_MODES = {"random", "big-vs-small", "small-models", "custom"}
BATCH_SIZE = 10_000


async def migrate_comparisons(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
) -> None:
    """
    Step 2: migrate conversations → comparison table.

    Requires: system_message_map.pkl
    Produces: comparison_map.pkl (conversation_pair_id → comparison uuid)
    """
    ensure_maps_dir(maps_dir)

    system_map: dict[str, uuid.UUID] = load_map(maps_dir, "system_message_map")
    comparison_map: dict[str, uuid.UUID] = {}

    inserted = 0
    skipped = 0
    batch_idx = 0

    with source_connection(source_uri, stream=True) as conn:
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
                        "system_msg_a_id": system_map.get(system_prompt_a) if system_prompt_a else None,
                        "system_msg_b_id": system_map.get(system_prompt_b) if system_prompt_b else None,
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
                comparison_map[pair_id] = comp_id

            if commit and rows_to_insert:
                async with get_session() as session:
                    await session.execute(sa_insert(Comparison), rows_to_insert)
                    await session.commit()

            inserted += len(rows_to_insert)
            logger.info(f"Batch {batch_idx}: {len(rows_to_insert)} comparisons processed.")
            batch_idx += 1

    logger.info(f"Done: {inserted} inserted, {skipped} skipped.")
    save_map(maps_dir, "comparison_map", comparison_map)
