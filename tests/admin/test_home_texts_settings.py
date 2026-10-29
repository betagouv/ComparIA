"""
Tests for the arena home texts accepted by PATCH /admin/settings.

Run with pytest, or directly:
    uv run python tests/admin/test_home_texts_settings.py
"""

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.database.models.app_settings import AppSettingsPatch  # noqa: E402

FIELDS = ("home_title", "home_prompt_placeholder", "home_banner")


@pytest.mark.parametrize("field", FIELDS)
def test_keeps_written_texts_trimmed(field):
    patch = AppSettingsPatch(
        **{field: {"fr": "  Posez votre question, deux IA vous répondent "}}
    )
    assert getattr(patch, field) == {
        "fr": "Posez votre question, deux IA vous répondent"
    }


@pytest.mark.parametrize("field", FIELDS)
def test_drops_empty_locales(field):
    patch = AppSettingsPatch(**{field: {"fr": "Bonjour", "en": "  ", "da": None}})
    assert getattr(patch, field) == {"fr": "Bonjour"}


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize(
    "value",
    [
        None,
        {"xx": "Hello"},
        {"fr": 3},
        {"fr": {"title": "Bonjour"}},
        {"fr": "a" * 1001},
    ],
)
def test_refuses_what_the_home_page_cannot_show(field, value):
    with pytest.raises(ValidationError):
        AppSettingsPatch(**{field: value})


@pytest.mark.parametrize("field", ("home_title", "home_prompt_placeholder"))
def test_home_texts_stay_one_line(field):
    with pytest.raises(ValidationError):
        AppSettingsPatch(**{field: {"fr": "a" * 201}})


def test_banner_holds_a_few_sentences():
    banner = "**Outil de sensibilisation.** " + "a" * 900
    assert AppSettingsPatch(home_banner={"fr": banner}).home_banner == {"fr": banner}
    with pytest.raises(ValidationError):
        AppSettingsPatch(home_banner={"fr": "a" * 1001})


def test_left_out_texts_stay_out_of_the_patch():
    patch = AppSettingsPatch(votes_objective=1).model_dump(exclude_unset=True)
    assert patch == {"votes_objective": 1}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
