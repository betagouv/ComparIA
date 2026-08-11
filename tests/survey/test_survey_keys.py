"""
Tests for the slug a survey question/option gets on creation, and for the
select-vs-checkbox shape check on an answer.

The key is what an answer stores and what the dataset publishes, and it never
changes afterwards, so getting it from the label is worth pinning down. The
shape check is what stops a 'select' question, which the frontend renders as
radios, from silently accepting more than one option.

DB-free. Runnable either way:
    uv run python tests/survey/test_survey_keys.py
    pytest tests/survey/test_survey_keys.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend.survey.services import _check_answer_shape, _key  # noqa: E402


def test_accents_and_spaces_become_a_plain_slug():
    assert _key("Tranche d'âge") == "tranche_d_age"
    assert _key("Trop lente à répondre") == "trop_lente_a_repondre"
    assert _key("Réponse  très   claire") == "reponse_tres_claire"


def test_punctuation_collapses_and_never_hangs_off_the_ends():
    assert _key("  Femme / non-binaire  ") == "femme_non_binaire"
    assert _key("A/B testing") == "a_b_testing"
    assert _key("--edge--") == "edge"


def test_a_label_with_nothing_to_slug_gives_an_empty_key():
    # The service turns this into a 422 rather than storing a blank key.
    for label in ("!!!", "???", "   ", "…"):
        assert _key(label) == ""


def test_the_key_fits_the_column():
    assert len(_key("mot " * 60)) <= 100


def test_select_accepts_at_most_one_key():
    _check_answer_shape("select", [])
    _check_answer_shape("select", ["a"])
    try:
        _check_answer_shape("select", ["a", "b"])
    except ValueError:
        pass
    else:
        raise AssertionError("expected a ValueError for two keys on a select question")


def test_checkbox_group_accepts_any_number_of_keys():
    _check_answer_shape("checkbox_group", [])
    _check_answer_shape("checkbox_group", ["a"])
    _check_answer_shape("checkbox_group", ["a", "b", "c"])


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print(f"ok  {name}")
    print("all good")
