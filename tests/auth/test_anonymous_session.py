import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.auth.dependencies import RequiredAnomymous
from backend.auth.middleware import anonymous_middleware
from backend.auth.services import _hash
from backend.config import ANONYMOUS_SESSION_COOKIE


def test_first_anonymous_request_is_served_and_sets_session_cookie():
    app = FastAPI()
    app.middleware("http")(anonymous_middleware)

    @app.get("/anonymous")
    async def anonymous_route(anonymous_user_hash: RequiredAnomymous) -> dict:
        return {"anonymous_user_hash": anonymous_user_hash}

    response = TestClient(app).get("/anonymous")

    assert response.status_code == 200
    token = response.cookies.get(ANONYMOUS_SESSION_COOKIE)
    assert token
    assert response.json() == {"anonymous_user_hash": _hash(token)}
