import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import settings

logger = logging.getLogger("languia")


def _async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _warn_if_db_uri_lacks_tls(url: str) -> None:
    """Loud warning, not a hard fail: an unencrypted URI to a remote host may
    already be running in production, and refusing to start would turn a
    config gap into an outage."""
    if settings.LANGUIA_DEBUG:
        return
    parsed = urlparse(url)
    if parsed.hostname in (None, "localhost", "127.0.0.1") or "sslmode" in (
        parsed.query or ""
    ):
        return
    logger.warning(
        "COMPARIA_DB_URI points at a non-local host without sslmode set: "
        "the Postgres connection may be unencrypted."
    )


_engine: AsyncEngine | None = None
_export_client = False


def use_export_engine() -> None:
    """
    Ask for the export's engine rather than the arena's, before anything opens
    a connection. The export reads the whole comparison table against a
    database that is serving traffic: it gets two connections instead of a
    pool, so it cannot crowd the arena out of Postgres, and a statement
    timeout, so a read that hangs is not left holding vacuum back for ever.

    Two, not one: the long read holds a connection open for the whole run, and
    looks the models up on another while it goes. One deadlocks the export
    against itself.
    """
    global _export_client
    if _engine is not None:
        raise RuntimeError("the engine is already open")
    _export_client = True


def get_engine() -> AsyncEngine | None:
    global _engine
    if not settings.COMPARIA_DB_URI:
        return None
    if _engine is None:
        _warn_if_db_uri_lacks_tls(settings.COMPARIA_DB_URI)
        options = (
            {
                "pool_size": 2,
                "max_overflow": 0,
                "connect_args": {
                    "options": (
                        f"-c statement_timeout={settings.DATASET_STATEMENT_TIMEOUT_MS}"
                    )
                },
            }
            if _export_client
            else {}
        )
        _engine = create_async_engine(_async_url(settings.COMPARIA_DB_URI), **options)
    return _engine


async def init_db():
    engine = get_engine()
    if engine is None:
        raise RuntimeError("COMPARIA_DB_URI is not configured")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("COMPARIA_DB_URI is not configured")
    async with AsyncSession(engine) as session:
        yield session
