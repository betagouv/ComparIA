"""
Tests for the audience measurement setting: the admin's choice between the
server's environment, their own Matomo and Off (no DB).
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.auth.router as auth_router  # noqa: E402
from tests.auth.test_oidc_settings import _settings_row  # noqa: E402
from tests.settings.test_cookie_banner import settings_client  # noqa: E402
from utils.database.models.app_settings import AppSettings  # noqa: E402


def test_a_new_instance_follows_the_server_setting():
    assert AppSettings().matomo_enabled is None


def test_admin_switches_measurement_off_and_back_to_the_server_setting():
    with settings_client() as client:
        before = client.get("/admin/settings").json()["matomo_enabled"]
        off = client.patch("/admin/settings", json={"matomo_enabled": False})
        kept = client.patch("/admin/settings", json={"votes_objective": 10})
        back = client.patch("/admin/settings", json={"matomo_enabled": None})

    assert before is None
    assert off.status_code == 200
    assert off.json()["matomo_enabled"] is False
    assert kept.json()["matomo_enabled"] is False
    assert back.status_code == 200
    assert back.json()["matomo_enabled"] is None


@pytest.mark.parametrize(
    "url, stored",
    [
        ("https://stats.example.org", "https://stats.example.org"),
        ("https://stats.example.org/matomo/", "https://stats.example.org/matomo"),
        (
            "https://stats.example.org:8443/matomo",
            "https://stats.example.org:8443/matomo",
        ),
        ("http://localhost:8080", "http://localhost:8080"),
        ("http://127.0.0.1/matomo", "http://127.0.0.1/matomo"),
        ("http://[::1]:8080/", "http://[::1]:8080"),
    ],
)
def test_admin_sets_a_matomo_address(url, stored):
    with settings_client() as client:
        response = client.patch("/admin/settings", json={"matomo_url": url})

    assert response.status_code == 200
    assert response.json()["matomo_url"] == stored


@pytest.mark.parametrize(
    "url",
    [
        "http://stats.example.org",
        "ftp://stats.example.org",
        "stats.example.org",
        "https://",
        "https:///matomo",
        "https://stats.example.org/?idsite=1",
        "https://stats.example.org/#top",
        "https://admin@stats.example.org",
        "https://admin:secret@stats.example.org",
        "http://localhost.evil.test",
        "https://stats.example.org/mat omo",
        "https://stats.example.org/it's",
        'https://stats.example.org/"quoted"',
        "https://stats.example.org/<script>",
        "https://stats.example.org/a>b",
        "https://stats.example.org/back\\slash",
        "https://stats.example.org/`tick`",
    ],
)
def test_a_bad_matomo_address_is_refused(url):
    with settings_client() as client:
        response = client.patch("/admin/settings", json={"matomo_url": url})
        after = client.get("/admin/settings").json()["matomo_url"]

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "matomo_url_invalid"
    assert after is None


def test_admin_sets_a_site_id():
    with settings_client() as client:
        response = client.patch("/admin/settings", json={"matomo_site_id": " 12 "})

    assert response.status_code == 200
    assert response.json()["matomo_site_id"] == "12"


@pytest.mark.parametrize("site_id", ["12a", "-1", "1.5", "١٢"])
def test_a_site_id_with_anything_but_digits_is_refused(site_id):
    with settings_client() as client:
        response = client.patch("/admin/settings", json={"matomo_site_id": site_id})

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "matomo_site_id_invalid"


def test_admin_switches_on_with_an_address_and_site_id():
    with settings_client() as client:
        response = client.patch(
            "/admin/settings",
            json={
                "matomo_enabled": True,
                "matomo_url": "https://stats.example.org/matomo",
                "matomo_site_id": "12",
            },
        )

    assert response.status_code == 200
    assert response.json()["matomo_enabled"] is True


def test_on_alone_takes_the_stored_address_and_site_id():
    with settings_client(
        matomo_enabled=False,
        matomo_url="https://stats.example.org",
        matomo_site_id="12",
    ) as client:
        response = client.patch("/admin/settings", json={"matomo_enabled": True})

    assert response.status_code == 200
    assert response.json()["matomo_enabled"] is True


@pytest.mark.parametrize(
    "stored, body",
    [
        ({}, {"matomo_enabled": True}),
        ({}, {"matomo_enabled": True, "matomo_url": "https://stats.example.org"}),
        ({}, {"matomo_enabled": True, "matomo_site_id": "12"}),
        (
            {"matomo_url": "https://stats.example.org", "matomo_site_id": "12"},
            {"matomo_enabled": True, "matomo_url": ""},
        ),
        (
            {
                "matomo_enabled": True,
                "matomo_url": "https://stats.example.org",
                "matomo_site_id": "12",
            },
            {"matomo_url": None},
        ),
        (
            {
                "matomo_enabled": True,
                "matomo_url": "https://stats.example.org",
                "matomo_site_id": "12",
            },
            {"matomo_site_id": ""},
        ),
    ],
)
def test_on_is_refused_without_both_an_address_and_a_site_id(stored, body):
    with settings_client(**stored) as client:
        response = client.patch("/admin/settings", json=body)
        after = client.get("/admin/settings").json()

    assert response.status_code == 422
    assert response.json()["detail"] == "matomo_needs_url_and_site_id"
    assert after["matomo_enabled"] == stored.get("matomo_enabled")
    assert after["matomo_url"] == stored.get("matomo_url")


def test_off_keeps_the_address_and_site_id():
    with settings_client(
        matomo_enabled=True,
        matomo_url="https://stats.example.org",
        matomo_site_id="12",
    ) as client:
        off = client.patch("/admin/settings", json={"matomo_enabled": False})
        server = client.patch("/admin/settings", json={"matomo_enabled": None})

    for response in (off, server):
        assert response.status_code == 200
        assert response.json()["matomo_url"] == "https://stats.example.org"
        assert response.json()["matomo_site_id"] == "12"


def test_public_config_reports_the_measurement_setting():
    for setting in (None, False, True):
        row = _settings_row(
            matomo_enabled=setting,
            matomo_url="https://stats.example.org",
            matomo_site_id="12",
        )

        async def get_app_settings(row=row):
            return row

        with patch.object(auth_router, "get_app_settings", get_app_settings):
            config = asyncio.run(auth_router.get_config())

        assert config.matomo_enabled is setting
        assert config.matomo_url == "https://stats.example.org"
        assert config.matomo_site_id == "12"
