import logging
import uuid
from datetime import datetime

import polars as pl
from sqlalchemy import text

from utils.database.models.messages.system import SystemMessage
from utils.database.session import get_session

from .migrate_utils import NOT_ARCHIVED, ensure_maps_dir, save_map, source_connection

logger = logging.getLogger("comparia.db.migrate")

QUERY = f"""
    SELECT DISTINCT content FROM (
        SELECT system_prompt_a AS content FROM conversations WHERE system_prompt_a IS NOT NULL AND system_prompt_a <> '' AND {NOT_ARCHIVED}
        UNION
        SELECT system_prompt_b AS content FROM conversations WHERE system_prompt_b IS NOT NULL AND system_prompt_b <> '' AND {NOT_ARCHIVED}
    ) sub
"""


async def migrate_system_messages(
    *,
    source_uri: str,
    commit: bool = False,
    maps_dir: str = "/tmp/comparia_migration",
) -> None:
    """
    Step 1: migrate distinct system prompts → system_message table.

    Produces: system_message_map.pkl (content → uuid)
    """
    ensure_maps_dir(maps_dir)

    system_map: dict[str, uuid.UUID] = {}
    to_insert: list[SystemMessage] = []

    with source_connection(source_uri) as conn:
        rows = pl.read_database(query=text(QUERY), connection=conn)

    for row in rows.iter_rows(named=True):
        content = row["content"]
        if content in system_map:
            continue
        msg_id = uuid.uuid4()
        system_map[content] = msg_id
        to_insert.append(SystemMessage(id=msg_id, content=content, created_at=datetime(2025, 2, 21, 15, 54, 42, 365103)))

    logger.info(f"Found {len(to_insert)} distinct system prompts.")

    if commit and to_insert:
        async with get_session() as session:
            session.add_all(to_insert)
            await session.commit()
        logger.info(f"Inserted {len(to_insert)} system_message rows.")
    else:
        logger.info(f"Dry run: would insert {len(to_insert)} system_message rows.")

    save_map(maps_dir, "system_message_map", system_map)
