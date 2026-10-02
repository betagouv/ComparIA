"""
Tests for the guard holding arena writes until the required signup questions
are answered, and for the writes it lets through.

DB-free. Runnable either way:
    uv run python tests/survey/test_arena_gate.py
    pytest tests/survey/test_arena_gate.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("ALTCHA_HMAC_KEY", "test")

from fastapi import HTTPException  # noqa: E402

import backend.survey.dependencies as dependencies  # noqa: E402


def _request(method: str, route_name: str):
    return SimpleNamespace(
        method=method, scope={"route": SimpleNamespace(name=route_name)}
    )


def _guard(request, user=SimpleNamespace(id=uuid.uuid4()), answered=False):
    original = dependencies.signup_questions_answered

    async def fake_answered(**_):
        return answered

    dependencies.signup_questions_answered = fake_answered
    try:
        return asyncio.run(dependencies.require_answered_questions(user, request))
    finally:
        dependencies.signup_questions_answered = original


def test_an_unanswered_account_is_held_on_a_write():
    try:
        _guard(_request("POST", "vote"))
    except HTTPException as error:
        assert error.status_code == 428
        return
    raise AssertionError("a write went through with the questions unanswered")


def test_reads_and_anonymous_visitors_are_never_held():
    _guard(_request("GET", "list_comparisons"))
    _guard(_request("POST", "vote"), user=None)


def test_claiming_past_comparisons_is_not_held():
    """The sign-in form merges before it asks the questions: holding the merge
    would lose it whenever the questions are closed unanswered."""
    _guard(_request("POST", "merge_comparisons"))


if __name__ == "__main__":
    test_an_unanswered_account_is_held_on_a_write()
    test_reads_and_anonymous_visitors_are_never_held()
    test_claiming_past_comparisons_is_not_held()
    print("ok")
