import logging
from datetime import date, datetime, time, timedelta
from typing import Awaitable

from sqlmodel import case, col, func, select

from backend.config import settings
from utils.database.models import Comparison, Turn
from utils.database.session import get_session
from utils.storage.redis import get_redis_client

from .models import (
    ActivityPoint,
    PreferenceCounts,
    PreferencePoint,
    StatisticsGranularity,
    StatisticsPeriod,
    StatisticsSummary,
)

logger = logging.getLogger("languia")


def _period_start(period: StatisticsPeriod, today: date) -> date | None:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period)
    return today - timedelta(days=days - 1) if days else None


def _granularity(period: StatisticsPeriod) -> StatisticsGranularity:
    return "month" if period == "all" else "week" if period == "90d" else "day"


def _bucket(column, granularity: StatisticsGranularity):
    return func.date_trunc(granularity, column)


def _next_bucket(value: date, granularity: StatisticsGranularity) -> date:
    if granularity == "day":
        return value + timedelta(days=1)
    if granularity == "week":
        return value + timedelta(days=7)
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


async def get_statistics_summary(
    period: StatisticsPeriod = "30d", ttl: int = 120
) -> StatisticsSummary:
    """Return public, aggregate statistics for non-archived comparisons."""

    cache_key = f"statistics:summary:{period}"
    client = get_redis_client()
    try:
        cached = client.get(cache_key)
        assert not isinstance(cached, Awaitable)
        if cached is not None:
            return StatisticsSummary.model_validate_json(cached)
    except Exception as error:
        logger.debug("Statistics summary cache miss: %s", error)

    granularity = _granularity(period)
    start = _period_start(period, date.today())
    empty = StatisticsSummary(
        period=period,
        granularity=granularity,
        prompts_count=0,
        conversations_count=0,
        models_count=0,
        preferences=PreferenceCounts(a_better=0, b_better=0, both_good=0, both_bad=0),
        activity=[],
        preference_activity=[],
    )
    if not settings.COMPARIA_DB_URI:
        logger.warning("Cannot compute statistics: no database configured")
        return empty

    comparison_filters = [col(Comparison.archived).is_not(True)]
    turn_filters = [col(Comparison.archived).is_not(True)]
    preference_filters = [col(Comparison.archived).is_not(True)]
    if start:
        start_at = datetime.combine(start, time.min)
        comparison_filters.append(col(Comparison.created_at) >= start_at)
        turn_filters.append(col(Turn.created_at) >= start_at)
        preference_filters.append(col(Turn.voted_at) >= start_at)

    async with get_session() as session:
        prompts_count, conversations_count = (
            await session.exec(
                select(
                    func.count(func.distinct(Turn.id)),
                    func.count(func.distinct(Comparison.id)),
                )
                .select_from(Comparison)
                .join(Turn)
                .where(*turn_filters)
            )
        ).one()

        model_ids = (
            select(Comparison.llm_id_a.label("model_id"))
            .where(*comparison_filters)
            .union(
                select(Comparison.llm_id_b.label("model_id")).where(*comparison_filters)
            )
            .subquery()
        )
        models_count = (
            await session.exec(select(func.count()).select_from(model_ids))
        ).one()

        activity_bucket = _bucket(Turn.created_at, granularity)
        prompt_rows = (
            await session.exec(
                select(activity_bucket, func.count(col(Turn.id)))
                .join(Comparison)
                .where(*turn_filters)
                .group_by(activity_bucket)
                .order_by(activity_bucket)
            )
        ).all()

        conversation_bucket = _bucket(Comparison.created_at, granularity)
        conversation_rows = (
            await session.exec(
                select(conversation_bucket, func.count(col(Comparison.id)))
                .where(*comparison_filters)
                .group_by(conversation_bucket)
                .order_by(conversation_bucket)
            )
        ).all()

        preference_bucket = _bucket(Turn.voted_at, granularity)
        preference_rows = (
            await session.exec(
                select(
                    preference_bucket,
                    *[
                        func.sum(case((Turn.choice == choice, 1), else_=0))
                        for choice in ("a_better", "b_better", "both_good", "both_bad")
                    ],
                )
                .join(Comparison)
                .where(*preference_filters, Turn.choice != None, Turn.choice != "idk")
                .group_by(preference_bucket)
                .order_by(preference_bucket)
            )
        ).all()

    def normalize_bucket(value: datetime | date) -> date:
        return value.date() if isinstance(value, datetime) else value

    prompts_by_date = {normalize_bucket(day): count for day, count in prompt_rows}
    conversations_by_date = {
        normalize_bucket(day): count for day, count in conversation_rows
    }
    preferences_by_date = {
        normalize_bucket(day): (a_better, b_better, both_good, both_bad)
        for day, a_better, b_better, both_good, both_bad in preference_rows
    }
    observed_dates = (
        prompts_by_date.keys()
        | conversations_by_date.keys()
        | preferences_by_date.keys()
    )
    if start:
        first_bucket = start
        if granularity == "week":
            first_bucket -= timedelta(days=first_bucket.weekday())
    elif observed_dates:
        first_bucket = min(observed_dates)
    else:
        first_bucket = date.today().replace(day=1)
    last_bucket = date.today()
    if granularity == "week":
        last_bucket -= timedelta(days=last_bucket.weekday())
    elif granularity == "month":
        last_bucket = last_bucket.replace(day=1)
    activity_dates = []
    bucket_date = first_bucket
    while bucket_date <= last_bucket:
        activity_dates.append(bucket_date)
        bucket_date = _next_bucket(bucket_date, granularity)
    activity = [
        ActivityPoint(
            date=day,
            prompts=prompts_by_date.get(day, 0),
            conversations=conversations_by_date.get(day, 0),
        )
        for day in activity_dates
    ]
    preference_activity = [
        PreferencePoint(
            date=day,
            a_better=preferences_by_date.get(day, (0, 0, 0, 0))[0],
            b_better=preferences_by_date.get(day, (0, 0, 0, 0))[1],
            both_good=preferences_by_date.get(day, (0, 0, 0, 0))[2],
            both_bad=preferences_by_date.get(day, (0, 0, 0, 0))[3],
        )
        for day in activity_dates
    ]
    preferences = PreferenceCounts(
        a_better=sum(point.a_better for point in preference_activity),
        b_better=sum(point.b_better for point in preference_activity),
        both_good=sum(point.both_good for point in preference_activity),
        both_bad=sum(point.both_bad for point in preference_activity),
    )
    summary = StatisticsSummary(
        period=period,
        granularity=granularity,
        prompts_count=prompts_count,
        conversations_count=conversations_count,
        models_count=models_count,
        preferences=preferences,
        activity=activity,
        preference_activity=preference_activity,
    )

    try:
        client.setex(cache_key, ttl, summary.model_dump_json())
    except Exception as error:
        logger.error("Could not cache statistics summary: %s", error)
    return summary
