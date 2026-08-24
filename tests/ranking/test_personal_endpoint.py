"""
Access control on the personal ranking endpoint (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/ranking/test_personal_endpoint.py
"""

import contextlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.ranking.router as ranking_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.dependencies import require_user  # noqa: E402
from backend.ranking.models import PersonalRanking  # noqa: E402
from utils.database.models.auth import User  # noqa: E402


def client(user: User | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(ranking_router.router)
    if user:
        app.dependency_overrides[require_user] = lambda: user
    return TestClient(app)


@contextlib.contextmanager
def ranking_of(asked_for: list):
    async def get_personal_ranking(user_id):
        asked_for.append(user_id)
        return PersonalRanking(rows=[], votes_count=0)

    original = ranking_router.get_personal_ranking
    ranking_router.get_personal_ranking = get_personal_ranking
    try:
        yield
    finally:
        ranking_router.get_personal_ranking = original


def test_a_signed_out_visitor_is_refused_rather_than_given_an_empty_ranking():
    response = client().get("/api/ranking/personal")

    assert response.status_code == 401
    assert response.json()["detail"] == "auth_required"


def test_a_signed_in_user_is_ranked_on_their_own_votes():
    user = User(email="personne@example.test")
    asked_for: list = []

    with ranking_of(asked_for):
        response = client(user).get("/api/ranking/personal")

    assert response.status_code == 200
    assert response.json() == {"rows": [], "votes_count": 0}
    assert asked_for == [user.id]


if __name__ == "__main__":
    for name, test in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            test()
