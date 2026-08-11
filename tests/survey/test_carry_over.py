"""
Unit tests for folding an anonymous respondent's survey history into the
account they just signed into (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/survey/test_carry_over.py
"""

import asyncio
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import utils.database.models  # noqa: E402,F401 needed before importing the services
from backend.survey.services import carry_over_anonymous  # noqa: E402
from utils.database.models.survey import SurveyPromptLog  # noqa: E402
from utils.database.models.utils import utc_now  # noqa: E402


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    """Replays a queued result per exec() and collects every execute()."""

    def __init__(self, *results):
        self.results = list(results)
        self.statements = []
        self.added = []

    async def exec(self, _statement):
        return FakeResult(self.results.pop(0) if self.results else [])

    async def execute(self, statement):
        self.statements.append(statement)

    def add(self, value):
        self.added.append(value)


def _log(question_id, shown_count, last_shown_at, *, anonymous):
    return SurveyPromptLog(
        question_id=question_id,
        user_id=None if anonymous else uuid.uuid4(),
        anonymous_user_hash="hash" if anonymous else None,
        shown_count=shown_count,
        last_shown_at=last_shown_at,
    )


def test_the_answer_just_given_replaces_the_one_on_the_account():
    """
    The login form asks the signup questions of returning users too, so both
    sides can hold an answer to the same question. The newer one wins, which
    means the account's rows for those questions are deleted before the
    anonymous ones are moved across.
    """
    user_id = uuid.uuid4()
    question_id = uuid.uuid4()

    # First exec: the questions this anonymous session just answered.
    session = FakeSession([question_id], [], [])
    asyncio.run(carry_over_anonymous(session, "hash", user_id))

    deletes = [
        statement
        for statement in session.statements
        if statement.__visit_name__ == "delete"
    ]
    assert deletes, "the account's own answer was left in place"
    target = str(deletes[0].compile(compile_kwargs={"literal_binds": True}))
    assert "survey_answer" in target
    assert "user_id" in target


def test_nothing_is_deleted_when_the_session_answered_nothing():
    """A plain sign-in must not touch the answers already on the account."""
    user_id = uuid.uuid4()

    session = FakeSession([], [], [])
    asyncio.run(carry_over_anonymous(session, "hash", user_id))

    assert not [
        statement
        for statement in session.statements
        if statement.__visit_name__ == "delete"
    ]


def test_prompt_counts_are_added_together_rather_than_duplicated():
    """
    Both sides can hold a row for the same question, and the readers key their
    lookup on question_id alone. Leaving two rows would let one quietly win and
    hand the respondent back showings they had already used up.
    """
    user_id = uuid.uuid4()
    question_id = uuid.uuid4()
    earlier = utc_now() - timedelta(days=3)
    later = utc_now()

    account_log = _log(question_id, 1, earlier, anonymous=False)
    account_log.user_id = user_id
    anonymous_log = _log(question_id, 2, later, anonymous=True)

    session = FakeSession([], [anonymous_log], [account_log])
    asyncio.run(carry_over_anonymous(session, "hash", user_id))

    assert account_log.shown_count == 3
    assert account_log.last_shown_at == later
    # The anonymous row is removed rather than reassigned, so exactly one row
    # survives for this question.
    assert anonymous_log.user_id is None


def test_an_unmatched_anonymous_row_is_reassigned_untouched():
    user_id = uuid.uuid4()
    question_id = uuid.uuid4()
    shown_at = utc_now()
    anonymous_log = _log(question_id, 2, shown_at, anonymous=True)

    session = FakeSession([], [anonymous_log], [])
    asyncio.run(carry_over_anonymous(session, "hash", user_id))

    assert anonymous_log.user_id == user_id
    assert anonymous_log.anonymous_user_hash is None
    assert anonymous_log.shown_count == 2
    assert anonymous_log in session.added


def test_the_cap_still_holds_after_a_merge():
    """Three showings anonymously plus one on the account must not read as one."""
    from utils.database.models.survey import MAX_QUESTION_PROMPTS

    user_id = uuid.uuid4()
    question_id = uuid.uuid4()
    account_log = _log(question_id, 1, utc_now(), anonymous=False)
    account_log.user_id = user_id
    anonymous_log = _log(question_id, 2, utc_now(), anonymous=True)

    session = FakeSession([], [anonymous_log], [account_log])
    asyncio.run(carry_over_anonymous(session, "hash", user_id))

    assert account_log.shown_count >= MAX_QUESTION_PROMPTS


if __name__ == "__main__":
    test_the_answer_just_given_replaces_the_one_on_the_account()
    test_nothing_is_deleted_when_the_session_answered_nothing()
    test_prompt_counts_are_added_together_rather_than_duplicated()
    test_an_unmatched_anonymous_row_is_reassigned_untouched()
    test_the_cap_still_holds_after_a_merge()
    print("ok")
