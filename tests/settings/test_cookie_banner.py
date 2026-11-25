"""
Tests for the cookie banner settings: switch, admin text and legal status (no DB).

Run with pytest, or directly:
    uv run python tests/settings/test_cookie_banner.py
"""

import asyncio
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.admin.legal as admin_legal  # noqa: E402
import backend.admin.router as admin_router  # noqa: E402
import backend.admin.settings as admin_settings  # noqa: E402
import backend.auth.router as auth_router  # noqa: E402
import backend.settings.informational_legal as informational_legal  # noqa: E402
import backend.utils.locale as locale_module  # noqa: E402
from backend.auth.dependencies import require_admin  # noqa: E402
from backend.settings import legal  # noqa: E402
from tests.auth.test_oidc_settings import _settings_row  # noqa: E402
from utils.database.models.app_settings import AppSettings  # noqa: E402

BANNER_URL = "/admin/legal/cookies"
# Pages with no content at all trip the status listing on their own.
EXTERNAL_PAGES = {
    key: {"mode": "external", "external_url": "https://example.test"}
    for key in ("legal_notice", "accessibility", "ecodesign")
}


def banner_payload(**overrides):
    payload = {
        "title": "Cookies",
        "description": "Nous utilisons des cookies.",
        "audience_measurement_label": "Mesure d’audience",
        "audience_measurement_description": "Compter les visites.",
        "remembered_settings_label": "Réglages mémorisés",
        "remembered_settings_description": "Garder la langue et le thème.",
    }
    payload.update(overrides)
    return payload


@contextmanager
def admin_client(cookie_banner=None, cookie_banner_enabled=False, signed_in=True):
    """The admin router over an in-memory settings row."""
    row = SimpleNamespace(
        cookie_banner=cookie_banner,
        cookie_banner_enabled=cookie_banner_enabled,
        legal_presentation=None,
        informational_legal_pages=EXTERNAL_PAGES,
        default_locale="fr",
        enabled_locales=["fr", "en"],
    )
    admin = SimpleNamespace(id=uuid.uuid4())

    async def get_app_settings():
        return row

    async def update_app_settings(values, updated_by=None):
        for key, value in values.items():
            setattr(row, key, value)
        return row

    async def no_document(_kind):
        return None

    app = FastAPI()
    app.include_router(admin_router.router)
    if signed_in:
        app.dependency_overrides[require_admin] = lambda: admin
    with (
        patch.object(locale_module, "get_app_settings", get_app_settings),
        patch.object(legal, "get_app_settings", get_app_settings),
        patch.object(informational_legal, "get_app_settings", get_app_settings),
        patch.object(admin_legal, "get_app_settings", get_app_settings),
        patch.object(admin_legal, "update_app_settings", update_app_settings),
        patch.object(admin_legal, "get_active_legal_document", no_document),
    ):
        yield TestClient(app), row


def test_banner_text_falls_back_to_the_default_when_nothing_is_stored():
    with admin_client() as (client, _):
        response = client.get(BANNER_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"fr", "en", "da"}
    assert body["en"]["title"] == "Cookies on this site"


def test_banner_text_falls_back_when_what_is_stored_no_longer_validates():
    with admin_client(cookie_banner={"fr": {"title": "Cookies"}}) as (client, _):
        body = client.get(BANNER_URL).json()

    assert body["fr"]["title"] == "Cookies sur ce site"


def test_admin_replaces_the_whole_text_and_reads_it_back():
    sent = {"fr": banner_payload(), "en": banner_payload(title="  Cookies here  ")}
    with admin_client() as (client, _):
        saved = client.put(BANNER_URL, json=sent)
        read_back = client.get(BANNER_URL).json()

    assert saved.status_code == 200
    assert set(read_back) == {"fr", "en"}
    assert read_back["fr"] == banner_payload()
    assert read_back["en"]["title"] == "Cookies here"


def test_blank_text_and_unknown_fields_are_refused():
    with admin_client() as (client, row):
        blank = client.put(BANNER_URL, json={"fr": banner_payload(title="   ")})
        extra = client.put(BANNER_URL, json={"fr": banner_payload(button="Ok")})
        unknown_locale = client.put(BANNER_URL, json={"xx": banner_payload()})

    assert blank.status_code == 422
    assert extra.status_code == 422
    assert unknown_locale.status_code == 422
    assert row.cookie_banner is None


def test_only_admins_read_or_change_the_text():
    with admin_client(signed_in=False) as (client, row):
        read = client.get(BANNER_URL)
        write = client.put(BANNER_URL, json={"fr": banner_payload()})

    assert read.status_code == 401
    assert write.status_code == 401
    assert row.cookie_banner is None


def cookies_status(client):
    return client.get("/admin/legal/status").json()["cookies"]


def test_cookies_status_is_unpublished_while_the_switch_is_off():
    with admin_client() as (client, _):
        status = cookies_status(client)

    assert status == {"published": False, "missing_locales": False}


def test_cookies_status_flags_enabled_languages_without_text():
    with admin_client(cookie_banner_enabled=True) as (client, _):
        defaults = cookies_status(client)
        client.put(BANNER_URL, json={"fr": banner_payload()})
        french_only = cookies_status(client)
        client.put(BANNER_URL, json={"fr": banner_payload(), "en": banner_payload()})
        complete = cookies_status(client)

    assert defaults == {"published": True, "missing_locales": False}
    assert french_only == {"published": True, "missing_locales": True}
    assert complete == {"published": True, "missing_locales": False}


@contextmanager
def settings_client(**overrides):
    row = _settings_row(**overrides)

    async def get_app_settings():
        return row

    async def update_app_settings(values, updated_by=None):
        for key, value in values.items():
            setattr(row, key, value)
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(id=uuid.uuid4())
    with (
        patch.object(admin_settings, "get_app_settings", get_app_settings),
        patch.object(admin_settings, "update_app_settings", update_app_settings),
    ):
        yield TestClient(app)


def test_admin_turns_the_switch_on_through_the_settings():
    with settings_client(cookie_banner_enabled=False) as client:
        before = client.get("/admin/settings").json()["cookie_banner_enabled"]
        patched = client.patch("/admin/settings", json={"cookie_banner_enabled": True})
        after = client.get("/admin/settings").json()["cookie_banner_enabled"]
        refused = client.patch("/admin/settings", json={"cookie_banner_enabled": None})

    assert before is False
    assert patched.status_code == 200
    assert after is True
    assert refused.status_code == 422


def test_the_switch_is_off_on_a_new_instance():
    assert AppSettings().cookie_banner_enabled is False
    assert AppSettings().cookie_banner is None


def test_switch_and_text_survive_a_save_to_the_database(database):
    from backend.admin.legal import (
        get_admin_legal_pages_status,
        get_cookie_banner,
        put_cookie_banner,
    )
    from backend.admin.settings import get_settings, patch_settings
    from utils.database.models.app_settings import AppSettingsPatch
    from utils.database.models.auth import User
    from utils.database.session import get_session
    from utils.database.settings import update_app_settings

    sent = legal.CookieBannerTranslatable.model_validate(
        {"fr": banner_payload(), "en": banner_payload(title="Cookies here")}
    )

    async def scenario():
        admin = User(email="admin@example.test", role="admin")
        async with get_session() as session:
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
        await update_app_settings(
            {
                "enabled_locales": ["fr", "en"],
                "default_locale": "fr",
                "informational_legal_pages": EXTERNAL_PAGES,
            },
            updated_by=admin.id,
        )
        await put_cookie_banner(sent, admin)
        await patch_settings(AppSettingsPatch(cookie_banner_enabled=True), admin)
        return (
            await get_cookie_banner(),
            await get_settings(),
            await get_admin_legal_pages_status(),
        )

    banner, settings, status = database(scenario)

    assert banner == sent
    assert settings.cookie_banner_enabled is True
    assert status["cookies"] == {"published": True, "missing_locales": False}


if __name__ == "__main__":
    for name, case in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            case()
            print(f"ok {name}")


def test_public_config_says_whether_the_banner_is_on():
    for enabled in (False, True):
        row = _settings_row(cookie_banner_enabled=enabled)

        async def get_app_settings(row=row):
            return row

        with patch.object(auth_router, "get_app_settings", get_app_settings):
            config = asyncio.run(auth_router.get_config())

        assert config.cookie_banner_enabled is enabled

