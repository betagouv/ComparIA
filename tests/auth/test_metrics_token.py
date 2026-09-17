"""
Who gets to read /metrics.

The endpoint used to answer everyone when METRICS_TOKEN was unset, so a
forgotten variable meant public metrics. It now refuses unless a token is
set and presented, except in debug.

Run with pytest, or directly:
    uv run python tests/auth/test_metrics_token.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.main as main  # noqa: E402


def get_metrics(token, debug=False, authorization=None):
    app = FastAPI()

    @app.get("/metrics", dependencies=[Depends(main._verify_metrics_token)])
    def metrics():
        return {"ok": True}

    headers = {"authorization": authorization} if authorization else {}
    with (
        patch.object(main.settings, "METRICS_TOKEN", token),
        patch.object(main.settings, "LANGUIA_DEBUG", debug),
    ):
        return TestClient(app).get("/metrics", headers=headers)


def test_no_token_configured_refuses_everyone():
    assert get_metrics(None).status_code == 401
    assert get_metrics("").status_code == 401


def test_no_token_configured_stays_open_in_debug():
    assert get_metrics(None, debug=True).status_code == 200


def test_the_right_bearer_gets_through():
    assert get_metrics("s3cret", authorization="Bearer s3cret").status_code == 200


def test_a_wrong_or_missing_bearer_is_refused():
    assert get_metrics("s3cret").status_code == 401
    assert get_metrics("s3cret", authorization="Bearer nope").status_code == 401
    assert get_metrics("s3cret", authorization="s3cret").status_code == 401


if __name__ == "__main__":
    test_no_token_configured_refuses_everyone()
    test_no_token_configured_stays_open_in_debug()
    test_the_right_bearer_gets_through()
    test_a_wrong_or_missing_bearer_is_refused()
    print("ok")
