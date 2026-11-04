"""POST /survey/answers when the database refuses the write."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

import backend.survey.router as survey_router
from backend.auth.dependencies import optional_user, require_anonymous


class ConflictingSession:
    rolled_back = False

    async def commit(self):
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    async def rollback(self):
        self.rolled_back = True


def test_a_concurrent_submission_is_a_conflict_not_a_crash(monkeypatch):
    session = ConflictingSession()

    @asynccontextmanager
    async def get_session():
        yield session

    async def submit_answers(*_args):
        pass

    async def terms_version(**_kwargs):
        return "v1"

    monkeypatch.setattr(survey_router, "get_session", get_session)
    monkeypatch.setattr(survey_router, "submit_answers", submit_answers)
    monkeypatch.setattr(
        survey_router, "get_current_terms_acceptance_version", terms_version
    )
    app = FastAPI()
    app.include_router(survey_router.router)
    app.dependency_overrides[optional_user] = lambda: None
    app.dependency_overrides[require_anonymous] = lambda: "a" * 64

    response = TestClient(app).post("/survey/answers", json={"answers": []})

    assert response.status_code == 409
    assert session.rolled_back
