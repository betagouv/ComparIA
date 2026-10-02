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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("ALTCHA_HMAC_KEY", "test")

import utils.database.models  # noqa: E402,F401 needed before importing the services
from backend.survey.services import (  # noqa: E402
    SurveyOptionUnknownError,
    submit_answers,
)
from utils.database.models.survey import (  # noqa: E402
    SurveyAnswerSubmit,
    SurveyQuestion,
    SurveyQuestionAnswer,
)

QUESTION_ID = uuid.uuid4()


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, held_keys):
        self.held_keys = held_keys
        self.added = []

    async def get(self, _model, _id):
        return SurveyQuestion(
            id=QUESTION_ID,
            key="age",
            triggers=["signup"],
            input_type="select",
            labels={"fr": "Âge"},
            options=[
                {"key": "18_24", "labels": {"fr": "18-24"}},
                {"key": "25_34", "labels": {"fr": "25-34"}},
                {"key": "under_25", "labels": {"fr": "-25"}, "archived": True},
            ],
        )

    async def exec(self, _statement):
        return FakeResult(self.held_keys)

    async def execute(self, _statement):
        pass

    def add(self, value):
        self.added.append(value)


def _submit(session, option_keys):
    payload = SurveyAnswerSubmit(
        answers=[SurveyQuestionAnswer(question_id=QUESTION_ID, option_keys=option_keys)]
    )
    asyncio.run(submit_answers(session, payload, uuid.uuid4(), None, "v1"))


def test_a_live_option_is_accepted():
    session = FakeSession([])
    _submit(session, ["25_34"])
    assert [answer.option_key for answer in session.added] == ["25_34"]


def test_an_archived_option_the_respondent_holds_can_be_kept():
    session = FakeSession(["under_25"])
    _submit(session, ["under_25"])
    assert [answer.option_key for answer in session.added] == ["under_25"]


def test_an_archived_option_cannot_be_newly_chosen():
    try:
        _submit(FakeSession([]), ["under_25"])
    except SurveyOptionUnknownError:
        return
    raise AssertionError("an archived option was accepted from someone not holding it")


if __name__ == "__main__":
    test_a_live_option_is_accepted()
    test_an_archived_option_the_respondent_holds_can_be_kept()
    test_an_archived_option_cannot_be_newly_chosen()
    print("ok")
