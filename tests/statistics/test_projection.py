"""The estimate drawn for the period still under way."""

import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "RAW")

from backend.statistics.projection import bucket_share, project  # noqa: E402

NOW = datetime(2026, 10, 8, 15, 30)  # a Thursday


def test_a_day_uses_the_profile_not_the_clock():
    share = bucket_share(
        datetime(2026, 10, 8), datetime(2026, 10, 9), NOW, "day", share_of_today=0.4
    )

    assert share == 0.4


def test_a_week_counts_its_full_days_and_part_of_today():
    # Monday to Wednesday are done, Thursday is 40% through its usual traffic.
    share = bucket_share(
        datetime(2026, 10, 5), datetime(2026, 10, 12), NOW, "week", share_of_today=0.4
    )

    assert share == (3 + 0.4) / 7


def test_an_hour_follows_the_clock():
    share = bucket_share(
        datetime(2026, 10, 8, 15), datetime(2026, 10, 8, 16), NOW, "hour", 0.0
    )

    assert share == 0.5


def test_too_early_in_the_period_there_is_no_estimate():
    assert project(120, 0.5) == 240
    assert project(12, 0.1) is None
