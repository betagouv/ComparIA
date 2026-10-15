"""
The admin's limits page: who may reach it, what a change must hold, and,
against a real Postgres (skipped where it is not installed), that a change is
stored with who made it and that the calibration reads a bounded sample.
"""

import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "RAW")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import backend.admin.limits as admin_limits  # noqa: E402
import backend.arena.limits as limits  # noqa: E402
from backend.activity.services import QueryTimedOutError  # noqa: E402
from backend.admin.router import router as admin_router  # noqa: E402
from backend.arena.models import AdminLimitsPatch  # noqa: E402
from backend.auth.dependencies import require_admin  # noqa: E402
from tests.admin.test_activity import (  # noqa: E402, F401
    NOW,
    activity,
    add_comparison,
    add_llms,
)
from utils.arena.calibrate import calibrate  # noqa: E402
from utils.database import session as session_module  # noqa: E402
from utils.storage import redis as redis_module  # noqa: E402

ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    """Nothing stored or read yet, and no Redis: the app settings cache then
    reads the database on every call."""
    monkeypatch.setattr(limits, "_stored", {})
    monkeypatch.setattr(limits, "_loaded_at", None)

    def no_redis():
        raise ConnectionError("no redis in tests")

    monkeypatch.setattr(redis_module, "get_redis_client", no_redis)


def client(admin=True):
    app = FastAPI()
    app.include_router(admin_router)
    if admin:

        async def fake_admin():
            return SimpleNamespace(id=ADMIN_ID)

        app.dependency_overrides[require_admin] = fake_admin
    return TestClient(app)


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/admin/limits"),
        ("patch", "/admin/limits"),
        ("get", "/admin/limits/calibration"),
    ],
)
def test_the_limits_need_an_admin(method, path):
    response = getattr(client(admin=False), method)(path)
    assert response.status_code == 401


@pytest.mark.parametrize(
    "body",
    [
        {"all_per_session": 0},
        {"expensive_per_ip": -1},
        # Less than a cent.
        {"expensive_per_session": 0.001},
        {"expensive_price_out": -1},
        {"all_per_ip": 2_147_483_648},
        {"all_per_session": 2.5},
        {"expected_answer_chars": -1},
        {"unknown": 1},
    ],
)
def test_a_value_the_arena_cannot_use_is_refused(body):
    assert client().patch("/admin/limits", json=body).status_code == 422


def test_only_the_values_sent_change(monkeypatch):
    received = {}

    async def update(changes, updated_by):
        received.update(changes=changes, updated_by=updated_by)
        raise RuntimeError("stop here")

    monkeypatch.setattr(admin_limits, "update_limit_settings", update)
    with pytest.raises(RuntimeError):
        client().patch(
            "/admin/limits",
            json={"all_per_session": 5_000, "expected_answer_chars": None},
        )
    # Null puts a value back on its default; one left out stays as it is.
    assert received == {
        "changes": {"all_per_session": 5_000, "expected_answer_chars": None},
        "updated_by": ADMIN_ID,
    }
    assert AdminLimitsPatch(expected_answer_chars=0).expected_answer_chars == 0


def test_the_expensive_limits_take_dollars_and_cents():
    patch = AdminLimitsPatch(
        expensive_per_session=0.4, expensive_per_ip=12.75, expensive_price_out=0
    )
    assert (patch.expensive_per_session, patch.expensive_per_ip) == (0.4, 12.75)
    # 0 makes every priced model expensive.
    assert patch.expensive_price_out == 0


def test_a_calibration_past_its_timeout_says_so(monkeypatch):
    async def slow():
        raise QueryTimedOutError()

    monkeypatch.setattr(admin_limits, "calibrate", slow)
    response = client().get("/admin/limits/calibration")
    assert response.status_code == 503
    assert response.json()["detail"] == "activity_query_timeout"


async def add_admin() -> None:
    async with session_module.get_session() as session:
        await session.execute(
            text(
                "INSERT INTO auth_user (id, email, role, created_at, last_seen_at)"
                " VALUES (:id, 'admin@example.org', 'admin', now(), now())"
            ),
            {"id": ADMIN_ID},
        )
        await session.commit()


def test_a_change_is_stored_with_who_made_it_and_applies_at_once(database, caplog):
    admin = SimpleNamespace(id=ADMIN_ID)

    async def scenario():
        await add_admin()
        before = await admin_limits.read_limits()
        changed = await admin_limits.patch_limits(
            AdminLimitsPatch(all_per_session=5_000, expected_answer_chars=0), admin
        )
        in_force = limits.setting("all_per_session")
        reset = await admin_limits.patch_limits(
            AdminLimitsPatch(all_per_session=None), admin
        )
        return before, changed, in_force, reset

    with caplog.at_level("INFO", "languia"):
        before, changed, in_force, reset = database(scenario)

    def by_name(page):
        return {limit.name: limit for limit in page.limits}

    assert not any(limit.stored for limit in before.limits)
    assert before.updated_by is None

    whole = by_name(changed)["all_per_session"]
    assert (whole.value, whole.stored) == (5_000, True)
    assert whole.default == limits.default("all_per_session")
    assert by_name(changed)["expected_answer_chars"].value == 0
    assert changed.updated_by == "admin@example.org"
    assert changed.updated_at is not None
    assert in_force == 5_000
    assert f"all_per_session set from default to 5,000 by admin {ADMIN_ID}" in (
        caplog.text
    )

    whole = by_name(reset)["all_per_session"]
    assert (whole.value, whole.stored) == (whole.default, False)
    # Left out of the second change, so still stored.
    assert by_name(reset)["expected_answer_chars"].stored
    assert limits.setting("all_per_session") == whole.default


@pytest.mark.parametrize("cap", [-1, 1_000_001, "inf"])
def test_a_daily_cap_the_arena_cannot_use_is_refused(cap):
    body = {"daily_usd_caps": {str(uuid.uuid4()): cap}}
    assert client().patch("/admin/limits", json=body).status_code == 422


def test_a_daily_cap_for_a_model_nobody_knows_is_refused(monkeypatch):
    async def update(caps, updated_by):
        raise admin_limits.UnknownLLMsError(set(caps))

    monkeypatch.setattr(admin_limits, "update_daily_caps", update)
    body = {"daily_usd_caps": {str(uuid.uuid4()): 5}}

    response = client().patch("/admin/limits", json=body)

    assert (response.status_code, response.json()["detail"]) == (422, "unknown_llm")


def test_daily_caps_are_stored_on_the_models_with_who_set_them(activity, caplog):
    admin = SimpleNamespace(id=ADMIN_ID)

    async def scenario():
        await add_admin()
        alpha, beta = await add_llms()
        await admin_limits.patch_limits(
            AdminLimitsPatch(daily_usd_caps={alpha: 12.5, beta: 3}), admin
        )
        await admin_limits.patch_limits(
            AdminLimitsPatch(daily_usd_caps={beta: None}), admin
        )
        async with session_module.get_session() as session:
            rows = await session.execute(
                text("SELECT name, daily_usd_cap FROM llm_data ORDER BY name")
            )
            return rows.all()

    with caplog.at_level("INFO", "languia"):
        caps = activity(scenario)

    assert [tuple(row) for row in caps] == [("Alpha", 12.5), ("Beta", None)]
    assert "daily cap of Alpha" in caplog.text
    assert f"from $3.00 to none by admin {ADMIN_ID}" in caplog.text


def test_the_calibration_reads_the_latest_comparisons_of_the_week(activity):
    async def scenario():
        llms = await add_llms()
        for minutes in range(3):
            await add_comparison(
                llms,
                created_at=NOW - timedelta(minutes=minutes),
                anonymous_user_hash=f"s{minutes}",
            )
        # Past the week: never read.
        await add_comparison(llms, created_at=NOW - timedelta(days=8))
        capped, whole_week = await calibrate(max_comparisons=2), await calibrate()
        # An archived model leaves the page.
        async with session_module.get_session() as session:
            await session.execute(
                text("UPDATE llm_data SET status = 'archived' WHERE name = 'Beta'")
            )
            await session.commit()
        return capped, whole_week, await admin_limits.read_limits()

    capped, whole_week, page = activity(scenario)

    assert (capped.comparisons, capped.capped) == (2, True)
    assert (whole_week.comparisons, whole_week.capped, whole_week.days) == (
        3,
        False,
        7,
    )
    assert {p.name for p in whole_week.proposals} == {
        "all_per_session",
        "all_per_ip",
        "expected_answer_chars",
    }
    # A typical message, in characters; nothing charged the expensive pool.
    assert whole_week.message_chars and whole_week.message_usd is None
    # Both test models are priced 0: never expensive, so no daily cap, and
    # worth a look.
    assert whole_week.daily_caps == []
    assert [(c.name, c.issue) for c in whole_week.price_checks] == [
        ("Alpha", "free"),
        ("Beta", "free"),
    ]
    assert [llm.name for llm in page.llms] == ["Alpha"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
