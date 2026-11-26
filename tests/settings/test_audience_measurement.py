"""
Tests for the audience measurement setting: the admin's choice between the
server's environment and Off (no DB).
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch

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


def test_on_is_refused_until_an_address_and_site_id_can_be_set():
    with settings_client() as client:
        response = client.patch("/admin/settings", json={"matomo_enabled": True})
        after = client.get("/admin/settings").json()["matomo_enabled"]

    assert response.status_code == 422
    assert after is None


def test_public_config_reports_the_measurement_setting():
    for setting in (None, False):
        row = _settings_row(matomo_enabled=setting)

        async def get_app_settings(row=row):
            return row

        with patch.object(auth_router, "get_app_settings", get_app_settings):
            config = asyncio.run(auth_router.get_config())

        assert config.matomo_enabled is setting
