"""
Tests for OIDC provider config: admin PATCH/GET endpoints (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc_settings.py
"""

import contextlib
import os
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.admin.router as admin_router  # noqa: E402
from backend.auth.dependencies import require_admin  # noqa: E402
from utils.database.models.auth import User  # noqa: E402


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


def _admin():
    return User(email="admin@example.test", role="admin")


def _settings_row(**overrides):
    fields = dict(
        auth_access_policy="anonymous_first",
        auth_domain_allowlist=[],
        votes_objective=300_000,
        platform_name="Test",
        primary_color_light="#000091",
        primary_color_dark="#8585F6",
        secondary_color_light="#6A6AF4",
        secondary_color_dark="#CACAFB",
        homepage_url=None,
        logo=None,
        logo_content_type=None,
        analysis_endpoint_id=None,
        analysis_model=None,
        publish_frequency="off",
        publish_hour=3,
        publish_timezone="UTC",
        enabled_locales=["fr"],
        default_locale="fr",
        auth_methods=["email_code"],
        oidc_issuer=None,
        oidc_client_id=None,
        oidc_client_secret_encrypted=None,
        oidc_scopes=["openid", "email"],
        oidc_button_label=None,
        oidc_button_logo=None,
        oidc_button_logo_content_type=None,
        updated_at=datetime(2026, 1, 1),
        updated_by=None,
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


@contextlib.contextmanager
def admin_client(row=None):
    if row is None:
        row = _settings_row()

    async def get_app_settings():
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = _admin

    with patched(admin_router, get_app_settings=get_app_settings):
        yield TestClient(app, raise_server_exceptions=True)


def test_get_settings_includes_auth_methods():
    with admin_client() as client:
        data = client.get("/admin/settings").json()
    assert data["auth_methods"] == ["email_code"]


def test_get_settings_oidc_fields_are_absent_by_default():
    with admin_client() as client:
        data = client.get("/admin/settings").json()
    assert data["oidc_issuer"] is None
    assert data["oidc_client_id"] is None
    assert data["oidc_has_client_secret"] is False
    assert data["oidc_scopes"] == ["openid", "email"]
    assert data["oidc_button_label"] is None
    assert data["oidc_has_button_logo"] is False
    assert data["oidc_button_logo_content_type"] is None


def test_patch_oidc_settings_encrypts_client_secret():
    """PATCH stores an encrypted token, not the plaintext secret."""
    patches = []

    async def update_app_settings(patch, updated_by):
        patches.append(patch)
        row = _settings_row(
            **{k: v for k, v in patch.items() if k != "oidc_client_secret"}
        )
        return row

    row = _settings_row()

    async def get_app_settings():
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = _admin

    with patched(
        admin_router,
        get_app_settings=get_app_settings,
        update_app_settings=update_app_settings,
    ):
        with TestClient(app) as client:
            response = client.patch(
                "/admin/settings", json={"oidc_client_secret": "super-secret"}
            )

    assert response.status_code == 200
    assert len(patches) == 1
    patch = patches[0]
    assert "oidc_client_secret" not in patch
    assert "oidc_client_secret_encrypted" in patch
    encrypted = patch["oidc_client_secret_encrypted"]
    assert encrypted != b"super-secret"

    from backend.auth.encryption import decrypt_oidc_secret

    assert decrypt_oidc_secret(encrypted) == "super-secret"


def test_get_settings_does_not_expose_plaintext_secret():
    """A row with an encrypted secret must not leak the plaintext to the API consumer."""
    from backend.auth.encryption import encrypt_oidc_secret

    row = _settings_row(oidc_client_secret_encrypted=encrypt_oidc_secret("hidden"))
    with admin_client(row) as client:
        data = client.get("/admin/settings").json()
    assert "oidc_client_secret" not in data
    assert "oidc_client_secret_encrypted" not in data
    assert data["oidc_has_client_secret"] is True


def test_patch_null_client_secret_clears_the_stored_value():
    patches = []

    async def update_app_settings(patch, updated_by):
        patches.append(patch)
        return _settings_row()

    row = _settings_row()

    async def get_app_settings():
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = _admin

    with patched(
        admin_router,
        get_app_settings=get_app_settings,
        update_app_settings=update_app_settings,
    ):
        with TestClient(app) as client:
            response = client.patch(
                "/admin/settings", json={"oidc_client_secret": None}
            )

    assert response.status_code == 200
    assert patches[0].get("oidc_client_secret_encrypted") is None


def test_patch_invalid_auth_method_is_rejected():
    with admin_client() as client:
        response = client.patch(
            "/admin/settings", json={"auth_methods": ["email_code", "unknown_method"]}
        )
    assert response.status_code == 422


def test_patch_empty_auth_methods_is_rejected():
    with admin_client() as client:
        response = client.patch("/admin/settings", json={"auth_methods": []})
    assert response.status_code == 422


def test_patch_oidc_enabled_auth_method_is_accepted():
    patches = []

    async def update_app_settings(patch, updated_by):
        patches.append(patch)
        return _settings_row(auth_methods=patch.get("auth_methods", ["email_code"]))

    row = _settings_row(
        oidc_issuer="https://idp.example.test",
        oidc_client_id="client-123",
        oidc_client_secret_encrypted=b"encrypted",
    )

    async def get_app_settings():
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = _admin

    with patched(
        admin_router,
        get_app_settings=get_app_settings,
        update_app_settings=update_app_settings,
    ):
        with TestClient(app) as client:
            response = client.patch(
                "/admin/settings", json={"auth_methods": ["email_code", "oidc"]}
            )

    assert response.status_code == 200
    assert patches[0]["auth_methods"] == ["email_code", "oidc"]


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
