from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import settings


def _async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


_engine: AsyncEngine | None = None
_export_client = False


def use_export_engine() -> None:
    """
    Ask for the export's engine rather than the arena's, before anything opens
    a connection. The export reads the whole comparison table against a
    database that is serving traffic: it gets one connection instead of a
    pool, so it cannot crowd the arena out of Postgres, and a statement
    timeout, so a read that hangs is not left holding vacuum back for ever.
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
        options = (
            {
                "pool_size": 1,
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
