import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("LOG_FORMAT", "RAW")
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://example/test")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.statistics import services  # noqa: E402
from utils.storage.redis import REDIS_INSTANCE_PREFIX  # noqa: E402


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def one(self):
        return self.rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self) -> None:
        self.statements = []
        # A day inside every period window, so the row lands in the activity
        # series whatever date the suite runs on.
        day = datetime.combine(date.today() - timedelta(days=1), time.min)
        self.results = [
            9,
            [(day, 42, 17)],
            [(day, 12)],
        ]

    async def exec(self, statement):
        self.statements.append(statement)
        return FakeResult(self.results[len(self.statements) - 1])


def test_get_statistics_summary_aggregates_activity(monkeypatch):
    session = FakeSession()

    @asynccontextmanager
    async def fake_get_session():
        yield session

    redis = Mock()
    redis.get.return_value = None
    monkeypatch.setattr(services, "get_session", fake_get_session)
    monkeypatch.setattr(services, "get_redis_client", lambda: redis)

    summary = asyncio.run(services.get_statistics_summary())

    assert summary.prompts_count == 42
    assert summary.conversations_count == 12
    assert summary.votes_count == 17
    assert summary.models_count == 9
    assert summary.range_end == services.date.today()
    activity_point = next(
        point
        for point in summary.activity
        if point.date == date.today() - timedelta(days=1)
    )
    assert activity_point.prompts == 42
    assert activity_point.conversations == 12
    assert len(session.statements) == 3
    redis.setex.assert_called_once()


def test_get_statistics_summary_uses_period_specific_cached_value(monkeypatch):
    redis = Mock()
    redis.get.return_value = """{
        "period":"7d","granularity":"day",
        "range_start":"2026-07-29","range_end":"2026-08-04","prompts_count":12,
        "conversations_count":5,"votes_count":4,"models_count":3,"activity":[]
    }"""
    monkeypatch.setattr(services, "get_redis_client", lambda: redis)

    summary = asyncio.run(services.get_statistics_summary("7d"))

    assert summary.prompts_count == 12
    assert summary.period == "7d"
    redis.get.assert_called_once_with(f"{REDIS_INSTANCE_PREFIX}statistics:summary:7d")
    redis.setex.assert_not_called()


def test_period_granularity_scales_with_range():
    assert services._granularity("7d") == "day"
    assert services._granularity("30d") == "day"
    assert services._granularity("90d") == "week"
    assert services._granularity("all") == "month"
