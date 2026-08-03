"""
Tests for the vote tag guard that replaced the Literal on keyword_annotations.

DB-free. Runnable either way:
    uv run python tests/vote_tags/test_check_vote_tags.py
    pytest tests/vote_tags/test_check_vote_tags.py
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.vote_tags.services as services  # noqa: E402
from backend.vote_tags.services import (  # noqa: E402
    UnknownVoteTagError,
    VoteTagSignMismatchError,
    check_vote_tags,
    expected_sign,
)
from utils.database.models.vote_tag import (  # noqa: E402
    RESERVED_NEGATIVE_KEYS,
    RESERVED_POSITIVE_KEYS,
)

ACTIVE = {
    **{key: "positive" for key in RESERVED_POSITIVE_KEYS},
    **{key: "negative" for key in RESERVED_NEGATIVE_KEYS},
    "well_sourced": "positive",
}


def check(keys, choice, pos):
    async def fake_signs():
        return ACTIVE

    with patch.object(services, "get_active_signs_by_key", fake_signs):
        asyncio.run(check_vote_tags(keys, choice, pos))


def test_expected_sign_matches_the_side_the_voter_praised():
    assert expected_sign("both_good", "a") == "positive"
    assert expected_sign("both_good", "b") == "positive"
    assert expected_sign("both_bad", "a") == "negative"
    assert expected_sign("both_bad", "b") == "negative"
    assert expected_sign("a_better", "a") == "positive"
    assert expected_sign("a_better", "b") == "negative"
    assert expected_sign("b_better", "a") == "negative"
    assert expected_sign("b_better", "b") == "positive"
    assert expected_sign("idk", "a") is None


def test_tags_matching_the_choice_are_accepted():
    check(["useful", "complete"], "a_better", "a")
    check(["incorrect"], "a_better", "b")
    check(["well_sourced"], "both_good", "b")


def test_no_tags_is_always_fine():
    check([], "idk", "a")
    check([], "both_good", "a")


def test_unknown_keys_are_rejected():
    for keys in (["banana"], ["useful", "banana"]):
        try:
            check(keys, "both_good", "a")
        except UnknownVoteTagError as error:
            assert "banana" in str(error)
        else:
            raise AssertionError(f"expected {keys} to be rejected")


def test_a_negative_tag_cannot_ride_on_a_positive_vote():
    # The bug this guard closes: until the taxonomy moved to the database
    # nothing checked the sign, so this used to be stored happily.
    try:
        check(["incorrect"], "both_good", "a")
    except VoteTagSignMismatchError as error:
        assert "incorrect" in str(error)
    else:
        raise AssertionError("expected a sign mismatch")


def test_skipping_the_vote_takes_no_tags():
    try:
        check(["useful"], "idk", "a")
    except VoteTagSignMismatchError:
        pass
    else:
        raise AssertionError("expected 'idk' to refuse tags")


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_") and callable(test):
            test()
            print(f"ok  {name}")
    print("all good")
