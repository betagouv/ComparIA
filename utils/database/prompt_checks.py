import logging
import uuid
from datetime import datetime

from sqlmodel import col, select

from backend.config import settings
from utils.database.models.prompt_check import DEFAULT_THRESHOLDS, PromptCheck
from utils.database.session import get_session
from utils.storage.redis import (
    REDIS_CHECK_FAILURES_KEY,
    REDIS_CHECK_WARNINGS_KEY,
    REDIS_PROMPT_CHECKS_KEY,
    get_redis_client,
    invalidate_cache,
    redis_cache,
)

logger = logging.getLogger("comparia.db")

# Consecutive failures after which the admin panel calls a check unhealthy.
# Both checks fail open, so nothing else makes an outage visible.
UNHEALTHY_AFTER_FAILURES = 3

# Used before the migration has run and when there is no database at all, so
# the admin panel and the arena see the same shape either way.
_DEFAULTS = [
    PromptCheck(id=index, kind=kind, mode="log", thresholds=dict(thresholds))
    for index, (kind, thresholds) in enumerate(DEFAULT_THRESHOLDS.items(), start=1)
]


@redis_cache(REDIS_PROMPT_CHECKS_KEY)
async def get_prompt_checks() -> list[PromptCheck]:
    if not settings.COMPARIA_DB_URI:
        return _DEFAULTS
    async with get_session() as session:
        query = select(PromptCheck).order_by(col(PromptCheck.id))
        return list((await session.exec(query)).all()) or _DEFAULTS


async def update_prompt_check(
    kind: str, patch: dict, updated_by: uuid.UUID
) -> PromptCheck | None:
    """Write one check. Returns None when 'kind' is not a seeded check."""
    async with get_session() as session:
        query = select(PromptCheck).where(col(PromptCheck.kind) == kind)
        row = (await session.exec(query)).first()
        if not row:
            return None

        for key, value in patch.items():
            setattr(row, key, value)
        row.updated_at = datetime.now()
        row.updated_by = updated_by

        session.add(row)
        await session.commit()
        await session.refresh(row)

    invalidate_cache(REDIS_PROMPT_CHECKS_KEY)
    return row


def get_warnings_shown(kind: str) -> int:
    """How many warnings of one check have been shown, counted by the arena.

    Read defensively: no redis, or no key, means nothing has been shown yet.
    """
    try:
        value = get_redis_client().get(REDIS_CHECK_WARNINGS_KEY.format(kind=kind))
        return int(value) if value else 0
    except Exception as e:
        logger.warning(f"[PROMPT CHECKS] Cannot read warnings shown for '{kind}': {e}")
        return 0


def get_consecutive_failures(kind: str) -> int:
    """Consecutive failures of one check, counted by the check runner.

    Read defensively: no redis, or no key, means nothing has failed.
    """
    try:
        value = get_redis_client().get(REDIS_CHECK_FAILURES_KEY.format(kind=kind))
        return int(value) if value else 0
    except Exception as e:
        logger.warning(f"[PROMPT CHECKS] Cannot read failures for '{kind}': {e}")
        return 0
