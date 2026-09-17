"""
What the logo endpoint is allowed to run.

The logo is admin-uploaded and may be an SVG, and an SVG opened as a document
carries its own <script>. The route answers with a sandbox policy, and the
site-wide header middleware has to leave that stricter policy alone.

Run with pytest, or directly:
    uv run python tests/auth/test_logo_headers.py
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.router as auth_router  # noqa: E402
from backend.main import security_headers_middleware  # noqa: E402

SVG_LOGO = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'


def get_logo(logo=SVG_LOGO, content_type="image/svg+xml"):
    async def get_app_settings():
        return SimpleNamespace(logo=logo, logo_content_type=content_type)

    app = FastAPI()
    app.include_router(auth_router.router)
    app.middleware("http")(security_headers_middleware)
    with patch.object(auth_router, "get_app_settings", get_app_settings):
        return TestClient(app).get("/auth/config/logo")


def test_an_svg_logo_is_served_without_scripting():
    response = get_logo()

    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    # sandbox with no allow-token is what actually turns scripting off.
    assert "sandbox" in policy
    assert "default-src 'none'" in policy
    assert response.headers["x-content-type-options"] == "nosniff"


def test_the_site_wide_policy_does_not_loosen_the_logo_one():
    site_wide = get_logo(logo=None).headers["content-security-policy"]
    assert "sandbox" not in site_wide

    assert "sandbox" in get_logo().headers["content-security-policy"]


if __name__ == "__main__":
    test_an_svg_logo_is_served_without_scripting()
    test_the_site_wide_policy_does_not_loosen_the_logo_one()
    print("ok")
