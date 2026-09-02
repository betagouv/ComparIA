"""
Unit test for the anonymous session cookie (no DB).

Run with pytest, or directly:
    uv run python tests/auth/test_anonymous_session.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.auth.dependencies import RequiredAnomymous  # noqa: E402
from backend.auth.middleware import anonymous_middleware  # noqa: E402
from backend.auth.services import _hash  # noqa: E402
from backend.config import ANONYMOUS_SESSION_COOKIE  # noqa: E402


def test_first_request_can_already_use_its_anonymous_session():
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


if __name__ == "__main__":
    test_first_request_can_already_use_its_anonymous_session()
