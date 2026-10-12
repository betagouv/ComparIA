"""
Tests for the leaderboard thresholds accepted by PATCH /admin/settings.

Run with pytest, or directly:
    uv run python tests/admin/test_ranking_settings.py
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.database.models.app_settings import AppSettingsPatch  # noqa: E402

FIELDS = ("ranking_min_votes", "ranking_max_rank_spread")


@pytest.mark.parametrize("field", FIELDS)
def test_accepts_zero_and_positive(field):
    assert getattr(AppSettingsPatch(**{field: 0}), field) == 0
    assert getattr(AppSettingsPatch(**{field: 50}), field) == 50


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [-1, None, 2.5, 2_147_483_648])
def test_refuses_values_the_column_cannot_hold(field, value):
    with pytest.raises(ValidationError):
        AppSettingsPatch(**{field: value})


def test_left_out_thresholds_stay_out_of_the_patch():
    patch = AppSettingsPatch(votes_objective=1).model_dump(exclude_unset=True)
    assert patch == {"votes_objective": 1}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
