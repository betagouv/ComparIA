from contextlib import asynccontextmanager, contextmanager
from logging import Logger
from typing import Any

import psycopg
from psycopg_pool import AsyncConnectionPool

from backend.config import settings

_async_pool: AsyncConnectionPool | None = None


async def open_async_pool() -> None:
    global _async_pool
    _async_pool = AsyncConnectionPool(settings.COMPARIA_DB_URI, open=False)
    await _async_pool.open()


async def close_async_pool() -> None:
    global _async_pool
    if _async_pool is not None:
        await _async_pool.close()
        _async_pool = None


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
    """Async db cursor using connection pool for FastAPI async endpoints."""
    if _async_pool is None:
        raise RuntimeError("Async connection pool is not initialized")
    try:
        logger.debug(f"[DB] Try to {action} data")

        async with _async_pool.connection() as conn:
            async with conn.cursor() as cursor:
                yield cursor

    except psycopg.Error as e:
        logger.error(f"[DB] Error couldn't {action} data: {e}", exc_info=True)
