"""
Unit tests for when the publish run is next due (no DB, no clock).

    uv run pytest tests/dataset/test_schedule.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend.publishing import next_run_at  # noqa: E402
from utils.database.models.app_settings import AppSettings  # noqa: E402

PARIS = "Europe/Paris"


def settings(frequency: str, hour: int = 3, timezone: str = PARIS) -> AppSettings:
    return AppSettings(
        id=1,
        publish_frequency=frequency,
        publish_hour=hour,
        publish_timezone=timezone,
    )


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=ZoneInfo("UTC"))


def local(moment: datetime | None) -> str:
    assert moment is not None
    return moment.astimezone(ZoneInfo(PARIS)).isoformat()


def test_off_is_never_due():
    assert next_run_at(settings("off"), utc("2026-08-04T12:00:00")) is None


def test_daily_waits_for_the_next_hour_it_has_not_passed():
    # 12:00 UTC is 14:00 in Paris: 03:00 has gone, so tomorrow.
    assert local(next_run_at(settings("daily"), utc("2026-08-04T12:00:00"))) == (
        "2026-08-05T03:00:00+02:00"
    )
    # 00:30 UTC is 02:30 in Paris: 03:00 is still to come today.
    assert local(next_run_at(settings("daily"), utc("2026-08-04T00:30:00"))) == (
        "2026-08-04T03:00:00+02:00"
    )


def test_weekly_means_monday_and_monthly_the_first():
    # Tuesday 4 August 2026 -> Monday 10 August.
    assert local(next_run_at(settings("weekly"), utc("2026-08-04T12:00:00"))) == (
        "2026-08-10T03:00:00+02:00"
    )
    assert local(next_run_at(settings("monthly"), utc("2026-08-04T12:00:00"))) == (
        "2026-09-01T03:00:00+02:00"
    )
    # From the 1st itself, once the hour has passed, the next month.
    assert local(next_run_at(settings("monthly"), utc("2026-08-01T12:00:00"))) == (
        "2026-09-01T03:00:00+02:00"
    )
    # A February start still lands on the first of March.
    assert local(next_run_at(settings("monthly"), utc("2026-02-15T12:00:00"))) == (
        "2026-03-01T03:00:00+01:00"
    )


def test_the_next_run_is_always_ahead():
    # Nothing catches up: whatever the moment, the answer is in the future.
    for frequency in ("daily", "weekly", "monthly"):
        for moment in (
            "2026-08-04T01:00:00",
            "2026-08-04T03:00:00",
            "2026-12-31T23:59:00",
        ):
            now = utc(moment)
            assert next_run_at(settings(frequency), now) > now


def test_the_hour_is_the_instance_hour_not_the_server_hour():
    tokyo = next_run_at(
        settings("daily", timezone="Asia/Tokyo"), utc("2026-08-04T12:00:00")
    )
    assert tokyo is not None
    assert tokyo.astimezone(ZoneInfo("Asia/Tokyo")).hour == 3
