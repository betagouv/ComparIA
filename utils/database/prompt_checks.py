import logging
import uuid
from datetime import datetime, timedelta

from sqlmodel import col, func, select

from backend.config import settings
from utils.database.models.prompt_check import (
    DEFAULT_CATEGORIES,
    DEFAULT_MODEL,
    PromptCheck,
)
from utils.database.models.turn import Turn
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


# Every decision a check can reach, so a quiet week still reports each bucket
# instead of dropping the ones at zero. Mirrors CheckResult.decision in
# backend/arena/checks.py, which cannot be imported here: it imports this module.
DECISIONS = ("pass", "logged", "warned", "blocked", "error")

# A year of turns is already more than any admin reads at once, and the bound
# keeps the scan from growing without limit.
MAX_STATS_DAYS = 365


def _prompt_check_turns(since: datetime) -> list:
    """Filters selecting the turns this check wrote, in the window.

    Records left by the older Nemotron guardrail have no `decision` key, and
    counting them would mix two different systems into one number.
    """
    return [
        col(Turn.created_at) > since,
        col(Turn.guardrail).has_key("decision"),
    ]


async def get_prompt_check_stats(days: int) -> dict:
    """What the check has been doing over the last `days` days.

    Every count is bounded by the window except the warning pair. The Redis
    counter behind `warnings_shown` has no timestamps, so `proceeded` is
    all-time too: measuring one against the other over different periods would
    give a ratio that means nothing, and that ratio is the point of the pair.
    """
    days = max(1, min(days, MAX_STATS_DAYS))
    stats: dict = {
        "days": days,
        "total": 0,
        "by_decision": {decision: 0 for decision in DECISIONS},
        "by_category": {},
        "proceeded": 0,
        "warnings_shown": get_warnings_shown(),
    }
    if not settings.COMPARIA_DB_URI:
        return stats

    where = _prompt_check_turns(datetime.now() - timedelta(days=days))
    decision = col(Turn.guardrail)["decision"].astext
    categories = (
        select(func.jsonb_object_keys(col(Turn.guardrail)["triggered"]).label("name"))
        .where(*where)
        .subquery()
    )

    async with get_session() as session:
        by_decision = (
            await session.exec(
                select(decision.label("decision"), func.count().label("count"))
                .where(*where)
                .group_by(decision)
            )
        ).all()
        by_category = (
            await session.exec(
                select(categories.c.name, func.count().label("count")).group_by(
                    categories.c.name
                )
            )
        ).all()
        proceeded = (
            await session.exec(
                select(func.count()).where(
                    col(Turn.guardrail).has_key("decision"),
                    decision == "warned",
                    col(Turn.guardrail)["user_proceeded"].astext == "true",
                )
            )
        ).one()

    for name, count in by_decision:
        stats["by_decision"][name] = count
    stats["total"] = sum(stats["by_decision"].values())
    stats["by_category"] = {name: count for name, count in by_category}
    stats["proceeded"] = proceeded
    return stats
