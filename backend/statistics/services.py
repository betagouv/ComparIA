import logging
from datetime import date, datetime, time, timedelta
from typing import Awaitable

from sqlmodel import and_, col, func, select

from backend.config import settings
from utils.database.models import Comparison, Turn
from utils.database.session import get_session
from utils.storage.redis import REDIS_STATISTICS_SUMMARY_KEY, get_redis_client

from .models import DailyConversationCount, StatisticsSummary

logger = logging.getLogger("languia")


async def get_statistics_summary(ttl: int = 120) -> StatisticsSummary:
    """Return the headline public statistics for non-archived comparisons."""

    client = get_redis_client()
    try:
        cached = client.get(REDIS_STATISTICS_SUMMARY_KEY)
        assert not isinstance(cached, Awaitable)
        if cached is not None:
            return StatisticsSummary.model_validate_json(cached)
    except Exception as error:
        logger.debug("Statistics summary cache miss: %s", error)

    if not settings.COMPARIA_DB_URI:
        logger.warning("Cannot compute statistics: no database configured")
        return StatisticsSummary(
            questions_count=0,
            votes_count=0,
            daily_conversations=[],
        )

    today = date.today()
    first_day = today - timedelta(days=13)
    async with get_session() as session:
        questions_count, votes_count = (
            await session.exec(
                select(
                    func.count(col(Turn.id)),
                    func.count(col(Turn.id)).filter(
                        and_(Turn.choice != None, Turn.choice != "idk")
                    ),
                )
                .join(Comparison)
                .where(col(Comparison.archived).is_not(True))
            )
        ).one()
        daily_rows = (
            await session.exec(
                select(func.date(Turn.created_at), func.count(col(Turn.id)))
                .join(Comparison)
                .where(
                    col(Comparison.archived).is_not(True),
                    col(Turn.created_at) >= datetime.combine(first_day, time.min),
                )
                .group_by(func.date(Turn.created_at))
                .order_by(func.date(Turn.created_at))
            )
        ).all()

    counts_by_date = {row_date: count for row_date, count in daily_rows}
    daily_conversations = [
        DailyConversationCount(
            date=first_day + timedelta(days=offset),
            count=counts_by_date.get(first_day + timedelta(days=offset), 0),
        )
        for offset in range(14)
    ]

    summary = StatisticsSummary(
        questions_count=questions_count,
        votes_count=votes_count,
        daily_conversations=daily_conversations,
    )

    try:
        client.setex(
            REDIS_STATISTICS_SUMMARY_KEY,
            ttl,
            summary.model_dump_json(),
        )
    except Exception as error:
        logger.error("Could not cache statistics summary: %s", error)

    return summary
