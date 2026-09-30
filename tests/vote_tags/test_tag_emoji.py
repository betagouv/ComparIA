"""
Tests for the emoji a vote tag carries.

The field is one character wide in the arena, so anything longer than an emoji
breaks the chip layout. The admin form accepted a whole word before this.

DB-free. Runnable either way:
    uv run python tests/vote_tags/test_tag_emoji.py
    pytest tests/vote_tags/test_tag_emoji.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from utils.database.models.vote_tag import VoteTagCreate  # noqa: E402


def _create(emoji: str) -> VoteTagCreate:
    return VoteTagCreate(sign="positive", emoji=emoji, labels={"fr": "Bien sourcee"})


@pytest.mark.parametrize("emoji", ["🙌", "💯", "🚩", "❌", "👨‍👩‍👧‍👦", "🏳️‍🌈"])
def test_emoji_is_accepted(emoji: str):
    # Including sequences of joined code points, which is why the column is 16
    # characters rather than one.
    assert _create(emoji).emoji == emoji


@pytest.mark.parametrize(
    "value", ["bien sourcee", "ok", "a", "5", "-", "…", "utile 🙌"]
)
def test_anything_that_is_not_an_emoji_is_refused(value: str):
    with pytest.raises(ValidationError):
        _create(value)


if __name__ == "__main__":
    for emoji in ["🙌", "💯", "🚩", "❌", "👨‍👩‍👧‍👦", "🏳️‍🌈"]:
        test_emoji_is_accepted(emoji)
    for value in ["bien sourcee", "ok", "a", "5", "-", "…", "utile 🙌"]:
        test_anything_that_is_not_an_emoji_is_refused(value)
    print("all good")
