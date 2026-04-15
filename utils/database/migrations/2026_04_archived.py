import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from utils.logger import configure_logger
from utils.utils import db_connection

from ..actions import rename_llm
from ..utils import TABLE_NAMES, reset_archived

MIGRATION_FILE = Path(__file__).parent / "2026_04_archived.sql"

SET_ARCHIVED_REASON_UNKNOWN = """
    UPDATE
        {table_name}
    SET
        archived_reason = 'unknown'
    WHERE
        archived = TRUE
        AND archived_reason IS NULL
    ;
"""

logger = logging.getLogger("comparia.db")


def migrate():
    logger.info("Start migration '2026_04_archived'.")

    with db_connection() as conn:
        try:
            # apply new column 'archived_reason' + 'archived_at'
            # remove 'archived' DEFAULT to FALSE
            conn.execute(text(MIGRATION_FILE.read_text()))
            conn.commit()
        except ProgrammingError as exc:
            if (
                '(psycopg2.errors.DuplicateColumn) column "archived_reason" of relation "conversations" already exists\n'
                in exc.args
            ):
                logger.warning(
                    f"Looks like base migration have already been applied, ignoring error."
                )
            else:
                raise

    # reset archived=False to NULL
    reset_archived()

    # rename what appears as a forgotten renames
    rename_llm("mistral-medium-3.1", "mistral-medium-2508", commit=True)
    rename_llm(
        "mistral-small-24B-Instruct-2501",
        "mistral-small-24b-instruct-2501",
        commit=True,
    )

    with db_connection() as conn:
        for table_name in TABLE_NAMES:
            results = conn.execute(
                text(SET_ARCHIVED_REASON_UNKNOWN.format(table_name=table_name))
            )
            logger.info(
                f"Set {results.rowcount} 'archived_reason' to 'unknown' on {table_name}."
            )
            conn.commit()

    logger.info("Finished migration '2026_04_archived'.")


if __name__ == "__main__":
    configure_logger(logger)
    migrate()
