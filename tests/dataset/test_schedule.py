"""Unit tests for the per-destination publication frequency."""

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend.publishing import next_run_at  # noqa: E402


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=ZoneInfo("UTC"))


def test_off_is_never_due():
    assert next_run_at("off", utc("2026-08-04T12:00:00")) is None


def test_daily_runs_at_the_fixed_hour():
    assert next_run_at("daily", utc("2026-08-04T01:00:00")) == utc(
        "2026-08-04T03:00:00"
    )
    assert next_run_at("daily", utc("2026-08-04T12:00:00")) == utc(
        "2026-08-05T03:00:00"
    )


def test_weekly_means_monday_and_monthly_the_first():
    assert next_run_at("weekly", utc("2026-08-04T12:00:00")) == utc(
        "2026-08-10T03:00:00"
    )
    assert next_run_at("monthly", utc("2026-08-04T12:00:00")) == utc(
        "2026-09-01T03:00:00"
    )


def test_the_next_run_is_always_ahead():
    for frequency in ("daily", "weekly", "monthly"):
        for moment in (
            "2026-08-04T01:00:00",
            "2026-08-04T03:00:00",
            "2026-12-31T23:59:00",
        ):
            now = utc(moment)
            assert next_run_at(frequency, now) > now
