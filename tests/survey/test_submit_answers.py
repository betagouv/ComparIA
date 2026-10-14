"""
Tests for which option keys an answer may carry.

A live option can be chosen by anyone. An option archived since it was chosen
stops being offered, but the person who holds it can send it back unchanged:
the profile page saves every question at once, so refusing it would make the
page unsavable for anyone whose answer was archived.

DB-free. Runnable either way:
    uv run python tests/survey/test_submit_answers.py
    pytest tests/survey/test_submit_answers.py
"""

import asyncio
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest
from pydantic_core import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("ALTCHA_HMAC_KEY", "test")

import utils.database.models  # noqa: E402,F401 needed before importing the services
from backend.survey.services import submit_answers  # noqa: E402
from utils.database.models.survey import (  # noqa: E402
    SurveyAnswer,
    SurveyAnswerSubmit,
    SurveyQuestion,
    SurveyQuestionAnswer,
)

QUESTION_ID = uuid.uuid4()


class FakeSession:
    def __init__(self):
        self.added = []

    async def execute(self, _statement):
        pass

    def add(self, value):
        self.added.append(value)


@contextmanager
def mock_db(monkeypatch: pytest.MonkeyPatch, answer=None):
    import backend.survey.services as survey_module

    async def logs(*args, **kwargs):
        return []

    async def answers(*args, **kwargs):
        if answer:
            return [
                SurveyAnswer(
                    question_id=QUESTION_ID,
                    value=answer,
                )
            ]
        return []

    async def questions(*args, **kwargs):
        return [
            SurveyQuestion(
                id=QUESTION_ID,
                key="age",
                input_type="select",
                labels={"fr": "Âge"},
                options=[
                    {"key": "18_24", "labels": {"fr": "18-24"}},
                    {"key": "25_34", "labels": {"fr": "25-34"}},
                    {"key": "under_25", "labels": {"fr": "-25"}, "archived": True},
                ],
            )
        ]

    monkeypatch.setattr(survey_module, "_all_answers", answers)
    monkeypatch.setattr(survey_module, "_all_logs", logs)
    monkeypatch.setattr(survey_module, "_all_questions", questions)

    yield


def _submit(session, value):
    payload = SurveyAnswerSubmit(
        answers=[SurveyQuestionAnswer(question_id=QUESTION_ID, value=value)]
    )
    asyncio.run(submit_answers(session, payload, uuid.uuid4(), None, "v1"))


def test_a_live_option_is_accepted(monkeypatch: pytest.MonkeyPatch):
    with mock_db(monkeypatch):
        session = FakeSession()
        _submit(session, "25_34")
        assert [answer.value for answer in session.added] == ["25_34"]


def test_an_archived_option_the_respondent_holds_can_be_kept(
    monkeypatch: pytest.MonkeyPatch,
):
    with mock_db(monkeypatch, "under_25"):
        session = FakeSession()
        _submit(session, "under_25")
        assert [answer.value for answer in session.added] == ["under_25"]


def test_an_archived_option_cannot_be_newly_chosen(monkeypatch: pytest.MonkeyPatch):
    with mock_db(monkeypatch):
        with pytest.raises(ValidationError):
            _submit(FakeSession(), "under_25")


if __name__ == "__main__":
    test_a_live_option_is_accepted()
    test_an_archived_option_the_respondent_holds_can_be_kept()
    test_an_archived_option_cannot_be_newly_chosen()
    print("ok")
