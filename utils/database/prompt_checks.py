import logging
import uuid
from datetime import datetime

from backend.config import settings
from utils.database.models.prompt_check import (
    DEFAULT_CATEGORIES,
    DEFAULT_MODEL,
    PromptCheck,
)
from utils.database.session import get_session
from utils.storage.redis import (
    REDIS_CHECK_FAILURES_KEY,
    REDIS_CHECK_WARNINGS_KEY,
    REDIS_PROMPT_CHECK_KEY,
    get_redis_client,
    invalidate_cache,
    redis_cache,
)

logger = logging.getLogger("comparia.db")

# Consecutive failures after which the admin panel calls the check unhealthy.
# It fails open, so nothing else makes an outage visible.
UNHEALTHY_AFTER_FAILURES = 3

# Used before the migration has run and when there is no database at all, so
# the admin panel and the arena see the same shape either way.
_DEFAULT = PromptCheck(
    id=1,
    model=DEFAULT_MODEL,
    categories={k: dict(v) for k, v in DEFAULT_CATEGORIES.items()},
)


@redis_cache(REDIS_PROMPT_CHECK_KEY)
async def get_prompt_check() -> PromptCheck:
    if not settings.COMPARIA_DB_URI:
        return _DEFAULT
    async with get_session() as session:
        return await session.get(PromptCheck, 1) or _DEFAULT


async def update_prompt_check(patch: dict, updated_by: uuid.UUID) -> PromptCheck:
    async with get_session() as session:
        row = await session.get(PromptCheck, 1)
        if not row:
            row = PromptCheck(
                id=1, categories={k: dict(v) for k, v in DEFAULT_CATEGORIES.items()}
            )

        for key, value in patch.items():
            setattr(row, key, value)
        row.updated_at = datetime.now()
        row.updated_by = updated_by

        session.add(row)
        await session.commit()
        await session.refresh(row)

    invalidate_cache(REDIS_PROMPT_CHECK_KEY)
    return row


def _read_counter(key: str, what: str) -> int:
    """Read defensively: no redis, or no key, means nothing has happened yet."""
    try:
        value = get_redis_client().get(key)
        return int(value) if value else 0
    except Exception as e:
        logger.warning(f"[PROMPT CHECK] Cannot read {what}: {e}")
        return 0


def get_warnings_shown() -> int:
    return _read_counter(REDIS_CHECK_WARNINGS_KEY, "warnings shown")


def get_consecutive_failures() -> int:
    return _read_counter(REDIS_CHECK_FAILURES_KEY, "consecutive failures")
