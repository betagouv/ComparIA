from contextlib import contextmanager
from logging import Logger
from typing import Any

import psycopg2

from backend.config import settings


@contextmanager
def db_cursor(action: str, logger: Logger, cursor_factory: Any = None) -> Any:
    """
    FIXME
    """
    try:
        logger.debug(f"[DB] Try to {action} data")

        with psycopg2.connect(settings.COMPARIA_DB_URI) as conn:
            with conn.cursor(cursor_factory=cursor_factory) as cursor:
                yield cursor

    except psycopg2.Error as e:
        logger.error(f"[DB] Error couldn't {action} data: {e}", exc_info=True)
        # FIXME Previous code never raise db error, raise it?
