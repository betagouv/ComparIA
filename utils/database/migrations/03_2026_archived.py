import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from utils.logger import configure_logger
from utils.utils import db_connection

from ..actions import rename_llm
from ..utils import reset_archived

MIGRATION_FILE = Path(__file__).parent / "03_2026_archived.sql"

SET_ARCHIVED_REASON_UNKNOWN = """
    UPDATE
        conversations
    SET
        archived_reason = 'unknown'
    WHERE
        archived = TRUE
        AND archived_reason IS NULL
    ;
"""

logger = logging.getLogger("comparia.database")


def migrate():
    logger.info("Start migration '03_2026_archived'.")

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
        results = conn.execute(text(SET_ARCHIVED_REASON_UNKNOWN))
        logger.info(
            f"Set {results.rowcount} 'archived_reason' to 'unknown' on conversations."
        )
        conn.commit()

    logger.info("Finished migration '03_2026_archived'.")


if __name__ == "__main__":
    configure_logger(logger)
    migrate()
