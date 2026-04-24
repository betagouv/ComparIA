import logging
from datetime import datetime

import polars as pl
from sqlalchemy import text

from backend.config import COUNTRY_PORTALS, DEFAULT_COUNTRY_PORTAL
from utils.utils import db_connection

from ..utils import archive

logger = logging.getLogger("comparia.db")

GET_ODD_COUNTRY_PORTALS = """
    SELECT
        country_portal,
        conversation_pair_id
    FROM
        conversations
    WHERE
        (
            archived IS NULL 
            OR archived = FALSE
        ) AND (
            country_portal IS NULL 
            OR country_portal NOT IN ({portals})
        )
    ;
"""
SET_COUNTRY_PORTAL_TO_FR = """
    UPDATE
        conversations
    SET
        country_portal = 'fr'
    WHERE
        conversation_pair_id IN ({ids})
    ;
"""


def archive_or_fix_country_portal(*, commit: bool = False) -> None:
    archived_at = datetime.now()

    with db_connection() as conn:
        data = pl.read_database(
            query=GET_ODD_COUNTRY_PORTALS.format(
                portals=", ".join(f"'{id}'" for id in COUNTRY_PORTALS)
            ),
            connection=conn,
        )

        if data.is_empty():
            logger.info("No unknown country_portal found!")
        for k, df in data.group_by("country_portal"):
            ids = df["conversation_pair_id"].to_list()

            if k[0] in (None, "en"):
                logger.warning(
                    f"Found {len(ids)} wrong country_portal '{k[0]}', will update as '{DEFAULT_COUNTRY_PORTAL}'."
                )
                results = conn.execute(
                    text(
                        SET_COUNTRY_PORTAL_TO_FR.format(
                            ids=", ".join(f"'{id}'" for id in ids)
                        )
                    )
                )
                if commit:
                    conn.commit()
                    logger.info(
                        f"Successfully updated {results.rowcount} conversation with country_portal '{k[0]}' to '{DEFAULT_COUNTRY_PORTAL}'."
                    )
                else:
                    logger.error(
                        f"{results.rowcount} conversation with country_portal '{k[0]}' should be updated to '{DEFAULT_COUNTRY_PORTAL}'."
                    )
            else:
                logger.warning(
                    f"Found {len(ids)} odd country_portal '{k[0]}' to archive as 'spam'."
                )
                archive("conversations", ids, "spam", archived_at, commit=commit)
