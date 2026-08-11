"""
Tests for the gate that holds back a login code until the signup questions
are answered.

It runs on /auth/email/request, so its failure modes are login failure modes:
an instance with nothing configured must never pay for it, and a caller whose
shape is unexpected must get the gate's own refusal rather than a 500.

DB-free. Runnable either way:
    uv run python tests/survey/test_signup_gate.py
    pytest tests/survey/test_signup_gate.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.survey.services as services  # noqa: E402
from utils.database.models.survey import SurveyQuestion  # noqa: E402


def _question(triggers=("signup",), required=True, archived_at=None):
    return SurveyQuestion(
        key="profession",
        triggers=list(triggers),
        required=required,
        input_type="select",
        labels={"fr": "Votre profession ?"},
        options=[
            {"key": "doctor", "labels": {"fr": "Médecin"}},
            {"key": "other", "labels": {"fr": "Autre"}},
        ],
        archived_at=archived_at,
    )


def _with_questions(questions, fn):
    original = services._all_questions

    async def fake_all_questions():
        return questions

    services._all_questions = fake_all_questions
    try:
        return asyncio.run(fn())
    finally:
        services._all_questions = original


def test_an_instance_with_no_questions_never_touches_the_database():
    """The common case. get_session is not stubbed here, so reaching the
    database would fail outright rather than pass quietly."""

    async def call():
        return await services.signup_questions_answered(
            user_id=None, anonymous_user_hash="hash"
        )

    assert _with_questions([], call) is True


def test_archived_questions_do_not_gate_anyone():
    async def call():
        return await services.signup_questions_answered(
            user_id=None, anonymous_user_hash="hash"
        )

    from utils.database.models.utils import utc_now

    assert _with_questions([_question(archived_at=utc_now())], call) is True


def test_after_vote_questions_do_not_gate_the_login():
    async def call():
        return await services.signup_questions_answered(
            user_id=None, anonymous_user_hash="hash"
        )

    assert _with_questions([_question(triggers=("after_vote",))], call) is True


def test_an_optional_signup_question_does_not_gate_the_login():
    """The whole point of the flag: the question is on the form and can be
    left blank, so adding one later locks nobody out."""

    async def call():
        return await services.signup_questions_answered(
            user_id=None, anonymous_user_hash="hash"
        )

    assert _with_questions([_question(required=False)], call) is True


def test_a_question_asked_at_both_moments_still_gates_the_login():
    """Naming the after-vote moment as well must not quietly turn a required
    signup question into an optional one."""

    async def call():
        return await services.signup_questions_answered(
            user_id=None, anonymous_user_hash=None
        )

    assert (
        _with_questions([_question(triggers=("signup", "after_vote"))], call) is False
    )


def test_a_caller_with_no_identity_is_refused_rather_than_raising():
    """
    A missing anonymous session cannot have answered anything. The route turns
    False into its own 428; a ValueError here would surface as a 500 on the
    login route instead.
    """

    async def call():
        return await services.signup_questions_answered(
            user_id=None, anonymous_user_hash=None
        )

    assert _with_questions([_question()], call) is False


def test_the_identity_check_still_rejects_two_identities():
    async def call():
        return await services.signup_questions_answered(
            user_id=uuid.uuid4(), anonymous_user_hash="hash"
        )

    try:
        _with_questions([_question()], call)
    except ValueError:
        return
    raise AssertionError("a respondent that is both an account and a session passed")


if __name__ == "__main__":
    test_an_instance_with_no_questions_never_touches_the_database()
    test_archived_questions_do_not_gate_anyone()
    test_after_vote_questions_do_not_gate_the_login()
    test_an_optional_signup_question_does_not_gate_the_login()
    test_a_question_asked_at_both_moments_still_gates_the_login()
    test_a_caller_with_no_identity_is_refused_rather_than_raising()
    test_the_identity_check_still_rejects_two_identities()
    print("ok")
