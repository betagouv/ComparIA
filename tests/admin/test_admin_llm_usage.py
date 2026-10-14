"""
What the admin reads of each model's day: its spend against its daily cap,
whether it rests, and how many of its answers came from the cache (no
network, no DB, no real Redis).
"""

import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "RAW")

import pytest  # noqa: E402

import backend.admin.llms.router as llms_router  # noqa: E402
import backend.arena.limits as limits  # noqa: E402
from tests.admin.test_admin_limits import client  # noqa: E402
from tests.arena.fakes import FakeRedis, fake_redis  # noqa: E402

FULL, BUSY, IDLE = uuid4(), uuid4(), uuid4()


def model(llm_id, name, cap):
    return SimpleNamespace(id=llm_id, name=name, daily_usd_cap=cap)


@pytest.fixture
def usage(monkeypatch):
    redis = FakeRedis()
    monkeypatch.setattr(limits, "now", lambda: redis.now)

    async def get_llms_data():
        return SimpleNamespace(
            enabled={
                FULL: model(FULL, "Full", 2.0),
                BUSY: model(BUSY, "Busy", None),
                IDLE: model(IDLE, "Idle", 10.0),
            }
        )

    monkeypatch.setattr(llms_router, "get_llms_data", get_llms_data)
    with fake_redis(limits, fake=redis):
        yield redis


def test_the_usage_needs_an_admin(usage):
    assert client(admin=False).get("/admin/llms/usage").status_code == 401


def test_each_model_s_day_against_its_cap(usage):
    day = limits.Day.at()
    limits.count_day(
        day,
        {
            FULL: {"usd": 2_500_000, "in": 9000, "out": 3000, "answers": 4},
            BUSY: {"usd": 1_200_000, "in": 100, "out": 50, "answers": 4, "cached": 1},
        },
    )

    response = client().get("/admin/llms/usage")

    assert response.status_code == 200
    rows = response.json()
    assert [row["name"] for row in rows] == ["Full", "Busy", "Idle"]
    assert rows[0] == {
        "llm_id": str(FULL),
        "name": "Full",
        "input_chars": 9000,
        "output_chars": 3000,
        "estimated_usd": 2.5,
        "cap_usd": 2.0,
        "resting": True,
        "resets_in": day.ends_in(),
        "answers": 4,
        "cached_answers": 0,
    }
    assert (rows[1]["resting"], rows[1]["cap_usd"], rows[1]["cached_answers"]) == (
        False,
        None,
        1,
    )
    assert (rows[2]["estimated_usd"], rows[2]["resting"]) == (0, False)
