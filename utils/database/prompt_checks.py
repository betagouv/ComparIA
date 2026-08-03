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

STATS_PERIODS = {
    "7d": (7, "day"),
    "30d": (30, "day"),
    "90d": (90, "day"),
    "365d": (365, "week"),
    "all": (None, "month"),
}


def _prompt_check_turns(since: datetime | None = None) -> list:
    """Filters selecting the turns this check wrote, in the window.

    Records left by the older Nemotron guardrail have no `decision` key, and
    counting them would mix two different systems into one number.
    """
    filters = [col(Turn.guardrail).has_key("decision")]
    if since is not None:
        filters.insert(0, col(Turn.created_at) >= since)
    return filters


def _next_bucket(value: datetime, bucket: str) -> datetime:
    if bucket == "day":
        return value + timedelta(days=1)
    if bucket == "week":
        return value + timedelta(days=7)
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    return value.replace(year=year, month=month)


async def get_prompt_check_stats(period: str = "all") -> dict:
    """Historical total and period-filtered activity for the admin dashboard."""
    if period not in STATS_PERIODS:
        period = "all"
    days, bucket = STATS_PERIODS[period]
    now = datetime.now()
    since = now - timedelta(days=days) if days is not None else None
    stats: dict = {
        "period": period,
        "bucket": bucket,
        "historical_total": 0,
        "total": 0,
        "by_decision": {decision: 0 for decision in DECISIONS},
        "by_category": {},
        "timeline": [],
    }
    if not settings.COMPARIA_DB_URI:
        return stats

    all_where = _prompt_check_turns()
    where = _prompt_check_turns(since)
    decision = col(Turn.guardrail)["decision"].astext
    categories = (
        select(
            func.jsonb_object_keys(col(Turn.guardrail)["triggered"]).label("name"),
            decision.label("decision"),
        )
        .where(*where)
        .subquery()
    )
    bucket_start = func.date_trunc(bucket, col(Turn.created_at)).label("bucket")

    async with get_session() as session:
        historical_total = (
            await session.exec(select(func.count()).where(*all_where))
        ).one()
        by_decision = (
            await session.exec(
                select(decision.label("decision"), func.count().label("count"))
                .where(*where)
                .group_by(decision)
            )
        ).all()
        by_category = (
            await session.exec(
                select(
                    categories.c.name,
                    categories.c.decision,
                    func.count().label("count"),
                ).group_by(
                    categories.c.name,
                    categories.c.decision,
                )
            )
        ).all()
        timeline = (
            await session.exec(
                select(bucket_start, decision.label("decision"), func.count())
                .where(*where)
                .group_by(bucket_start, decision)
                .order_by(bucket_start)
            )
        ).all()

    stats["historical_total"] = historical_total
    for name, count in by_decision:
        stats["by_decision"][name] = count
    stats["total"] = sum(stats["by_decision"].values())
    for category, name, count in by_category:
        stats["by_category"].setdefault(
            category, {decision: 0 for decision in DECISIONS}
        )[name] = count

    buckets: dict[datetime, dict[str, int]] = {}
    for start, name, count in timeline:
        buckets.setdefault(start, {decision: 0 for decision in DECISIONS})[name] = count
    if buckets:
        cursor = min(buckets)
        end = max(buckets)
        while cursor <= end:
            counts = buckets.get(cursor, {decision: 0 for decision in DECISIONS})
            stats["timeline"].append(
                {"date": cursor.date().isoformat(), "by_decision": counts}
            )
            cursor = _next_bucket(cursor, bucket)
    return stats
