import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from backend.config import settings

# Import all table models to populate SQLModel.metadata
from utils.database.models import Comparison, Turn  # noqa: F401
from utils.database.models.auth import (  # noqa: F401
    AuthSession,
    ConsentLog,
    LegalDocument,
    LoginCode,
    User,
)
from utils.database.models.llms import (  # noqa: F401
    LLMData,
    LLMEndpoint,
    LLMLab,
    LLMLicense,
)
from utils.database.models.messages import LLMMessage, UserMessage  # noqa: F401
from utils.database.models.prompt_check import (  # noqa: F401
    PromptCheck,
    PromptCheckResult,
)
from utils.database.models.suggestion import (  # noqa: F401
    PromptSuggestion,
    SuggestionCategory,
)
from utils.database.models.survey import (  # noqa: F401
    SurveyAnswer,
    SurveyPromptLog,
    SurveyQuestion,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url() -> str:
    url = settings.COMPARIA_DB_URI
    if not url:
        raise ValueError("COMPARIA_DB_URI is not set")
    # psycopg3 async driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
