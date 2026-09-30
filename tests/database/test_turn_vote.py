"""
Bounds on the annotations a voter can attach to a turn.

Both fields land in JSONB exactly as sent, so nothing downstream trims them.
Run with pytest, or directly:
    uv run python tests/database/test_turn_vote.py
"""

import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from backend.config import (  # noqa: E402
    MAX_VOTE_CUSTOM_ANNOTATION_LEN,
    MAX_VOTE_KEYWORD_ANNOTATIONS,
)
from utils.database.models import TurnVoteAnnotate  # noqa: E402


def annotate(**overrides) -> TurnVoteAnnotate:
    fields = {
        "turn_id": uuid4(),
        "pos": "a",
        "keyword_annotations": [],
        "custom_annotation": None,
    }
    return TurnVoteAnnotate(**{**fields, **overrides})


def test_a_reasonable_annotation_is_accepted():
    vote = annotate(keyword_annotations=["clear", "helpful"], custom_annotation="  ok ")

    assert vote.keyword_annotations == ["clear", "helpful"]
    assert vote.custom_annotation == "ok"


def test_the_keyword_list_is_bounded():
    with pytest.raises(ValidationError):
        annotate(keyword_annotations=["t"] * (MAX_VOTE_KEYWORD_ANNOTATIONS + 1))

    assert (
        len(
            annotate(
                keyword_annotations=[
                    f"t{i}" for i in range(MAX_VOTE_KEYWORD_ANNOTATIONS)
                ]
            ).keyword_annotations
        )
        == MAX_VOTE_KEYWORD_ANNOTATIONS
    )


def test_the_free_text_is_bounded():
    with pytest.raises(ValidationError):
        annotate(custom_annotation="a" * (MAX_VOTE_CUSTOM_ANNOTATION_LEN + 1))

    at_limit = annotate(custom_annotation="a" * MAX_VOTE_CUSTOM_ANNOTATION_LEN)
    assert at_limit.custom_annotation is not None


def test_repeated_keywords_are_dropped():
    """A tag says the same thing however many times it is sent; the order the
    voter picked them in survives."""
    vote = annotate(keyword_annotations=["clear", "helpful", "clear", "clear"])

    assert vote.keyword_annotations == ["clear", "helpful"]


def test_an_empty_annotation_is_stored_as_nothing():
    assert annotate(custom_annotation="   ").custom_annotation is None


def run():
    test_a_reasonable_annotation_is_accepted()
    test_the_keyword_list_is_bounded()
    test_the_free_text_is_bounded()
    test_repeated_keywords_are_dropped()
    test_an_empty_annotation_is_stored_as_nothing()
    print("Vote annotation cases passed.")


if __name__ == "__main__":
    run()
