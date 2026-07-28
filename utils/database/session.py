from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import settings


def _async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """
    Built on first use rather than at import time: importing this module, and
    everything importing it in turn, must not require a database to be
    configured.
    """
    if not settings.COMPARIA_DB_URI:
        raise RuntimeError("COMPARIA_DB_URI is not set")
    return create_async_engine(_async_url(settings.COMPARIA_DB_URI))


async def init_db():
    async with get_engine().begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(get_engine()) as session:
        yield session
