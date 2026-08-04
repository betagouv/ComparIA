import asyncio
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import Mock

os.environ.setdefault("LOG_FORMAT", "RAW")
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://example/test")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.statistics import services  # noqa: E402


class FakeResult:
    def one(self) -> tuple[int, int]:
        return 42, 17


class FakeSession:
    def __init__(self) -> None:
        self.statement = None

    async def exec(self, statement):
        self.statement = statement
        return FakeResult()


def test_get_statistics_summary_reads_both_counts_in_one_query(monkeypatch):
    session = FakeSession()

    @asynccontextmanager
    async def fake_get_session():
        yield session

    redis = Mock()
    redis.get.return_value = None
    monkeypatch.setattr(services, "get_session", fake_get_session)
    monkeypatch.setattr(services, "get_redis_client", lambda: redis)

    summary = asyncio.run(services.get_statistics_summary())

    assert summary.questions_count == 42
    assert summary.votes_count == 17
    assert session.statement is not None
    redis.setex.assert_called_once()


def test_get_statistics_summary_uses_cached_value(monkeypatch):
    redis = Mock()
    redis.get.return_value = '{"questions_count": 12, "votes_count": 5}'
    monkeypatch.setattr(services, "get_redis_client", lambda: redis)

    summary = asyncio.run(services.get_statistics_summary())

    assert summary.questions_count == 12
    assert summary.votes_count == 5
    redis.setex.assert_not_called()
