"""
Unit tests for the 'respondent' field added to each exported turn row.

These exercise the wiring inside `comparison_to_turns` only: given what
`get_survey_respondent_answers` returns, assert a turn row's `respondent`
field carries the right shape (JSON-encoded, keyed by the respondent that
had the comparison) and nothing else.

What this does NOT cover: the actual SQL in `get_survey_respondent_answers`
that restricts answers to published, non-archived questions
(`col(SurveyQuestion.published) == True`, `col(SurveyQuestion.archived_at
).is_(None)`) needs a live Postgres to exercise for real, so it is not
covered by these offline tests. Here, "only published questions" is
represented by the mocked return value already being the post-filter
result -- the same contract `comparison_to_turns` relies on in production.

No DB and no pytest required:
    uv run --group data python tests/dataset/test_respondent.py
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import tests.dataset.test_comparison_to_turns as fix  # noqa: E402
from utils.dataset import compute  # noqa: E402


def _turns_for(comp, respondent_answers: dict) -> list[dict]:
    """Run `comparison_to_turns` with `get_survey_respondent_answers` mocked."""

    async def _mock():
        return respondent_answers

    original = compute.get_survey_respondent_answers
    compute.get_survey_respondent_answers = _mock
    try:
        return asyncio.run(compute.comparison_to_turns(comp))
    finally:
        compute.get_survey_respondent_answers = original


def _one_turn_comparison():
    return fix.comparison(
        [fix.turn(fix.user_msg(), fix.llm_msg("a", 10), fix.llm_msg("b", 10))]
    )


def test_respondent_dict_only_has_published_questions_for_signed_in_user():
    user_id = uuid.uuid4()
    comp = _one_turn_comparison()
    comp.user_id = user_id
    comp.anonymous_user_hash = None

    # Stands in for the query's already-filtered result: an unpublished or
    # archived question's answer would simply never appear in this dict.
    respondent_answers = {
        f"user:{user_id}": {"age": "25_34", "job": ["dev", "student"]},
    }

    turns = _turns_for(comp, respondent_answers)
    assert len(turns) == 1
    assert json.loads(turns[0]["respondent"]) == {
        "age": "25_34",
        "job": ["dev", "student"],
    }


def test_respondent_dict_matches_anonymous_hash_when_no_user():
    comp = _one_turn_comparison()
    comp.user_id = None
    comp.anonymous_user_hash = "abc123"

    respondent_answers = {"anon:abc123": {"age": "35_44"}}

    turns = _turns_for(comp, respondent_answers)
    assert json.loads(turns[0]["respondent"]) == {"age": "35_44"}


def test_respondent_dict_empty_when_respondent_never_answered():
    comp = _one_turn_comparison()
    comp.user_id = None
    comp.anonymous_user_hash = "no-answers-for-this-one"

    turns = _turns_for(comp, {})
    assert json.loads(turns[0]["respondent"]) == {}


def test_respondent_dict_ignores_other_respondents_answers():
    """A dict keyed by someone else's user/hash must not leak in."""
    comp = _one_turn_comparison()
    comp.user_id = uuid.uuid4()
    comp.anonymous_user_hash = None

    respondent_answers = {f"user:{uuid.uuid4()}": {"age": "18_24"}}

    turns = _turns_for(comp, respondent_answers)
    assert json.loads(turns[0]["respondent"]) == {}


if __name__ == "__main__":
    test_respondent_dict_only_has_published_questions_for_signed_in_user()
    test_respondent_dict_matches_anonymous_hash_when_no_user()
    test_respondent_dict_empty_when_respondent_never_answered()
    test_respondent_dict_ignores_other_respondents_answers()
    print("All respondent tests passed.")
