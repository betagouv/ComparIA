from contextlib import asynccontextmanager, contextmanager
from logging import Logger
from typing import Any

import psycopg

from backend.config import settings


@contextmanager
def db_cursor(action: str, logger: Logger, cursor_factory: Any = None) -> Any:
    """Sync db cursor for non-async contexts (ranking scripts, etc.)."""
    try:
        logger.debug(f"[DB] Try to {action} data")

        with psycopg.connect(settings.COMPARIA_DB_URI) as conn:
            with conn.cursor(row_factory=cursor_factory) as cursor:
                yield cursor

    except psycopg.Error as e:
        logger.error(f"[DB] Error couldn't {action} data: {e}", exc_info=True)


@asynccontextmanager
async def async_db_cursor(action: str, logger: Logger) -> Any:
    """Async db cursor for FastAPI async endpoints."""
    try:
        logger.debug(f"[DB] Try to {action} data")

        async with await psycopg.AsyncConnection.connect(settings.COMPARIA_DB_URI) as conn:
            async with conn.cursor() as cursor:
                yield cursor

    except psycopg.Error as e:
        logger.error(f"[DB] Error couldn't {action} data: {e}", exc_info=True)
