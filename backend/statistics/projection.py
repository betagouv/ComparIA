"""
The last point of an activity chart is the period still under way, and drawn
as it stands it always looks like a collapse: at nine in the morning the day
holds a fraction of its messages. These helpers say how much of a typical
period has already gone by, so the chart can show an estimate of the whole
next to what has really been counted.
"""

from datetime import datetime, time, timedelta
from typing import Literal

from sqlmodel import col, func, literal, select
from sqlmodel.ext.asyncio.session import AsyncSession

from utils.database.models import Turn

Bucket = Literal["hour", "day", "week", "month"]

# Below this share of the period, an estimate multiplies a handful of
# messages by ten or more and says nothing: the chart leaves the point out.
MIN_SHARE = 0.15
# Days the intraday profile is read from, and the messages it needs before it
# is trusted over the clock.
PROFILE_DAYS = 28
PROFILE_MIN_MESSAGES = 200


async def day_share(session: AsyncSession, now: datetime) -> float:
    """Share of a typical day's messages sent before this time of day, read
    from the last four full weeks. Falls back to the share of the day elapsed
    on an instance too quiet to have a profile."""
    midnight = datetime.combine(now.date(), time.min)
    elapsed = now - midnight
    since_midnight = col(Turn.created_at) - func.date_trunc("day", col(Turn.created_at))
    before, total = (
        await session.exec(
            select(
                func.count().filter(since_midnight < literal(elapsed)),
                func.count(),
            ).where(
                col(Turn.created_at) >= midnight - timedelta(days=PROFILE_DAYS),
                col(Turn.created_at) < midnight,
            )
        )
    ).one()
    if total < PROFILE_MIN_MESSAGES:
        return elapsed / timedelta(days=1)
    return before / total


def bucket_share(
    bucket_start: datetime,
    bucket_end: datetime,
    now: datetime,
    bucket: Bucket,
    share_of_today: float,
) -> float:
    """Share of the bucket [bucket_start, bucket_end) that has gone by at `now`.
    Days count alike; only the current day is weighted by the profile."""
    if bucket == "hour":
        return (now - bucket_start) / (bucket_end - bucket_start)
    days = (bucket_end - bucket_start).days
    full_days = (datetime.combine(now.date(), time.min) - bucket_start).days
    return (full_days + share_of_today) / days


def project(count: int, share: float) -> int | None:
    return round(count / share) if share >= MIN_SHARE else None
