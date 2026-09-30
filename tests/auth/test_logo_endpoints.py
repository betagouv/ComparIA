"""
The platform and OIDC button logo endpoints, through the HTTP API (no DB).

Both logos are admin-uploaded, so both go through the same upload rules and the
same sandboxed response. These tests hold the two endpoints to one contract.

Run with pytest, or directly:
    uv run python tests/auth/test_logo_endpoints.py
"""

import contextlib
import os
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

import backend.admin.router as admin_router  # noqa: E402
import backend.auth.router as auth_router  # noqa: E402
from backend.auth.dependencies import require_admin  # noqa: E402
from backend.config import LOGO_SVG_MAX_SIZE, LOGO_UPLOAD_MAX_SIZE  # noqa: E402
from backend.main import security_headers_middleware  # noqa: E402
from tests.auth.test_oidc_settings import _admin, _settings_row, patched  # noqa: E402

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>'
SVG_WITH_SCRIPT = b'<svg xmlns="http://www.w3.org/2000/svg"><script>x()</script></svg>'

# One row per logo: how to upload it, where it is served, which columns hold it.
PLATFORM = SimpleNamespace(
    upload="/admin/settings/logo",
    served="/auth/config/logo",
    data="logo",
    content_type="logo_content_type",
)
OIDC = SimpleNamespace(
    upload="/admin/settings/oidc-logo",
    served="/auth/config/oidc/logo",
    data="oidc_button_logo",
    content_type="oidc_button_logo_content_type",
)
LOGOS = [pytest.param(PLATFORM, id="platform"), pytest.param(OIDC, id="oidc")]


def png() -> bytes:
    out = BytesIO()
    Image.new("RGB", (600, 600), (10, 120, 200)).save(out, format="PNG")
    return out.getvalue()


@contextlib.contextmanager
def logo_app(row=None, *, as_admin=True):
    """Both routers on one app, settings held in one mutable row."""
    row = row or _settings_row()

    async def get_app_settings():
        return row

    async def update_app_settings(patch, updated_by):
        for name, value in patch.items():
            setattr(row, name, value)
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.include_router(auth_router.router)
    app.middleware("http")(security_headers_middleware)
    if as_admin:
        app.dependency_overrides[require_admin] = _admin

    with (
        patched(admin_router, get_app_settings=get_app_settings),
        patched(admin_router, update_app_settings=update_app_settings),
        patched(auth_router, get_app_settings=get_app_settings),
    ):
        yield TestClient(app), row


def upload(client, logo, content, content_type):
    return client.put(logo.upload, files={"file": ("logo", content, content_type)})


@pytest.mark.parametrize("logo", LOGOS)
def test_only_an_admin_can_upload_or_delete_the_logo(logo):
    with logo_app(as_admin=False) as (client, row):
        assert upload(client, logo, png(), "image/png").status_code in (401, 403)
        assert client.delete(logo.upload).status_code in (401, 403)
        assert getattr(row, logo.data) is None


@pytest.mark.parametrize("logo", LOGOS)
def test_an_unsupported_type_is_refused(logo):
    with logo_app() as (client, row):
        response = upload(client, logo, b"GIF89a", "image/gif")

    assert response.status_code == 400
    assert response.json()["detail"] == "logo_unsupported_type"
    assert getattr(row, logo.data) is None


@pytest.mark.parametrize("logo", LOGOS)
def test_an_oversized_file_is_refused(logo):
    with logo_app() as (client, row):
        too_big = upload(client, logo, b"0" * (LOGO_UPLOAD_MAX_SIZE + 1), "image/png")
        big_svg = upload(client, logo, SVG + b" " * LOGO_SVG_MAX_SIZE, "image/svg+xml")

    assert too_big.status_code == 400
    assert too_big.json()["detail"] == "logo_too_large"
    assert big_svg.json()["detail"] == "logo_too_large"
    assert getattr(row, logo.data) is None


@pytest.mark.parametrize("logo", LOGOS)
def test_an_svg_with_a_script_is_refused(logo):
    with logo_app() as (client, row):
        response = upload(client, logo, SVG_WITH_SCRIPT, "image/svg+xml")

    assert response.status_code == 400
    assert response.json()["detail"] == "logo_invalid"
    assert getattr(row, logo.data) is None


@pytest.mark.parametrize("logo", LOGOS)
def test_a_png_is_stored_as_a_small_webp(logo):
    with logo_app() as (client, row):
        response = upload(client, logo, png(), "image/png")

    assert response.status_code == 200
    assert getattr(row, logo.content_type) == "image/webp"
    image = Image.open(BytesIO(getattr(row, logo.data)))
    assert image.format == "WEBP"
    assert max(image.size) < 600


@pytest.mark.parametrize("logo", LOGOS)
def test_deleting_the_logo_empties_it(logo):
    with logo_app() as (client, row):
        upload(client, logo, SVG, "image/svg+xml")
        assert getattr(row, logo.data) == SVG

        assert client.delete(logo.upload).status_code == 200

    assert getattr(row, logo.data) is None
    assert getattr(row, logo.content_type) is None


@pytest.mark.parametrize("logo", LOGOS)
def test_a_served_logo_is_sandboxed(logo):
    row = _settings_row(
        **{logo.data: SVG_WITH_SCRIPT, logo.content_type: "image/svg+xml"}
    )
    with logo_app(row) as (client, _):
        response = client.get(logo.served)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy
    assert "sandbox" in policy
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize("logo", LOGOS)
def test_no_logo_is_a_404(logo):
    with logo_app() as (client, _):
        assert client.get(logo.served).status_code == 404


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
