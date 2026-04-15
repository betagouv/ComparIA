import logging
from datetime import datetime

import polars as pl

from utils.utils import db_connection

from ..utils import TableName, archive

logger = logging.getLogger("comparia.db")

SHOULD_BE_ARCHIVED_QUERY = """
    SELECT
        d.conversation_pair_id,
        c.archived_reason
    FROM
        {table_name} d
    JOIN 
        conversations c ON d.conversation_pair_id = c.conversation_pair_id
    WHERE
        c.archived = TRUE
        AND (d.archived IS NULL OR d.archived = FALSE)
    ;
"""


def archive_not_archived(*, commit: bool = False) -> None:
    """
    Archive votes and reactions related to already archived conversations.
    """
    logger.info("Searching for not archived votes and reactions.")

    table_names: list[TableName] = ["votes", "reactions"]
    for table_name in table_names:
        with db_connection(stream=True) as conn:
            results = pl.read_database(
                query=SHOULD_BE_ARCHIVED_QUERY.format(table_name=table_name),
                connection=conn,
            )
            to_archive = (
                results.group_by("archived_reason").agg(pl.col("conversation_pair_id"))
            ).to_dicts()

        if not to_archive:
            logger.info(f"No {table_name} that should be archived found!")
            return

        archive_at = datetime.now()

        for group in to_archive:
            if ids := group["conversation_pair_id"]:
                logger.warning(
                    f"Found {len(ids)} {table_name} that should be archived with reason='{group["archived_reason"] or "unknown"}'."
                )
                archive(
                    table_name,
                    ids,
                    group["archived_reason"] or "unknown",
                    archive_at,
                    commit=commit,
                )
            else:
                logger.info(f"No {table_name} that should be archived found!")
