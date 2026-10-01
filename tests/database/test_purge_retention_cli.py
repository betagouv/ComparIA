"""The purge-retention command refuses periods that would wipe live data."""

import asyncio
import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402

from utils.database.retention import RetentionReport  # noqa: E402

# The package re-exports the function under the module's name.
action = importlib.import_module("utils.database.actions.purge_retention")


@pytest.mark.parametrize(
    "period",
    [
        "ip_months",
        "comparison_months",
        "session_months",
        "prompt_check_months",
        "consent_years",
    ],
)
def test_refuses_a_period_under_one(monkeypatch, period):
    async def never_called(*args, **kwargs):
        raise AssertionError("purged with a zero period")

    monkeypatch.setattr(action, "purge_expired_data", never_called)
    with pytest.raises(SystemExit):
        asyncio.run(action.purge_retention(**{period: 0}, apply=True))


def test_passes_the_periods_through(monkeypatch):
    seen = {}

    async def fake_purge(periods, apply):
        seen["periods"], seen["apply"] = periods, apply
        return RetentionReport()

    monkeypatch.setattr(action, "purge_expired_data", fake_purge)
    asyncio.run(action.purge_retention(ip_months=2, consent_years=6))

    assert seen["apply"] is False
    assert seen["periods"].ip_months == 2
    assert seen["periods"].comparison_months == 24
    assert seen["periods"].consent_years == 6
