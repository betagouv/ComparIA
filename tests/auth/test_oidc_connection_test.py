"""
Tests for the OIDC connection test and the gate it puts on removing the email
code sign-in (no DB, no Redis, no real identity provider).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc_connection_test.py
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

import backend.admin.router as admin_router  # noqa: E402
from backend.auth.dependencies import require_admin  # noqa: E402
from tests.auth.fake_oidc_provider import (  # noqa: E402
    ISSUER,
    FakeProvider,
    serving,
)
from tests.auth.test_oidc_settings import (  # noqa: E402
    _admin,
    _configured_oidc_row,
    patched,
)
from utils.secrets import encrypt_secret  # noqa: E402


@contextlib.contextmanager
def admin_session(row, provider=None):
    """An admin client over a settings row that `update_app_settings` really
    updates, so a test result stored by one request is seen by the next."""

    async def get_app_settings():
        return row

    async def update_app_settings(patch, updated_by):
        for key, value in patch.items():
            setattr(row, key, value)
        return row

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = _admin

    with (
        serving(provider or FakeProvider()),
        patched(
            admin_router,
            get_app_settings=get_app_settings,
            update_app_settings=update_app_settings,
        ),
    ):
        yield TestClient(app)


def _row(**overrides):
    # `_configured_oidc_row` points at another issuer than the fake provider's.
    fields = dict(
        oidc_issuer=ISSUER,
        oidc_client_id="client-123",
        auth_methods=["email_code", "oidc"],
        oidc_connection_test=None,
    )
    fields.update(overrides)
    return _configured_oidc_row(**fields)


def _test_connection(client):
    response = client.post("/admin/settings/oidc/test")
    assert response.status_code == 200, response.text
    return response.json()


def _remove_email_code(client):
    return client.patch("/admin/settings", json={"auth_methods": ["oidc"]})


def test_connection_test_passes_against_a_sound_provider():
    with admin_session(_row()) as client:
        result = _test_connection(client)
    assert result["passed"] is True
    assert result["reason"] is None


def test_connection_test_does_not_exchange_a_token():
    provider = FakeProvider()
    with admin_session(_row(), provider) as client:
        _test_connection(client)
    assert provider.requests_to("/token") == []
    assert provider.requests_to("/userinfo") == []


def test_connection_test_names_an_unreachable_provider():
    provider = FakeProvider()
    provider.unreachable = True
    with admin_session(_row(), provider) as client:
        assert _test_connection(client)["reason"] == "discovery_unreachable"


def test_connection_test_names_a_missing_discovery_document():
    provider = FakeProvider()
    provider.discovery = None
    with admin_session(_row(), provider) as client:
        assert _test_connection(client)["reason"] == "discovery_unreachable"


def test_connection_test_names_an_issuer_mismatch():
    provider = FakeProvider()
    provider.discovery["issuer"] = "https://elsewhere.test"
    with admin_session(_row(), provider) as client:
        assert _test_connection(client)["reason"] == "issuer_mismatch"


def test_connection_test_names_a_non_https_endpoint():
    provider = FakeProvider()
    provider.discovery["token_endpoint"] = "http://idp.example.test/token"
    with admin_session(_row(), provider) as client:
        assert _test_connection(client)["reason"] == "endpoint_not_https"


def test_connection_test_names_a_missing_endpoint():
    provider = FakeProvider()
    del provider.discovery["userinfo_endpoint"]
    with admin_session(_row(), provider) as client:
        assert _test_connection(client)["reason"] == "missing_endpoint"


def test_connection_test_names_an_unreadable_secret_without_calling_the_provider():
    provider = FakeProvider()
    row = _row(oidc_client_secret_encrypted=b"not-a-fernet-token")
    with admin_session(row, provider) as client:
        assert _test_connection(client)["reason"] == "secret_unreadable"
    assert provider.requests == []


def test_connection_test_names_an_incomplete_config():
    row = _row(oidc_client_secret_encrypted=None)
    with admin_session(row) as client:
        assert _test_connection(client)["reason"] == "incomplete_config"


def test_settings_show_the_result_of_the_test_on_the_current_config():
    with admin_session(_row()) as client:
        assert client.get("/admin/settings").json()["oidc_connection_test"] is None
        _test_connection(client)
        shown = client.get("/admin/settings").json()["oidc_connection_test"]
    assert shown["passed"] is True
    assert shown["tested_at"]


def test_settings_show_a_failed_test_with_its_reason():
    provider = FakeProvider()
    provider.unreachable = True
    with admin_session(_row(), provider) as client:
        _test_connection(client)
        shown = client.get("/admin/settings").json()["oidc_connection_test"]
    assert shown["passed"] is False
    assert shown["reason"] == "discovery_unreachable"


def test_removing_email_code_is_refused_without_a_test():
    row = _row()
    with admin_session(row) as client:
        response = _remove_email_code(client)
    assert response.status_code == 400
    assert row.auth_methods == ["email_code", "oidc"]


def test_removing_email_code_is_accepted_after_a_passing_test():
    row = _row()
    with admin_session(row) as client:
        _test_connection(client)
        response = _remove_email_code(client)
    assert response.status_code == 200, response.text
    assert row.auth_methods == ["oidc"]


def test_removing_email_code_is_refused_after_a_failing_test():
    provider = FakeProvider()
    provider.discovery["issuer"] = "https://elsewhere.test"
    row = _row()
    with admin_session(row, provider) as client:
        _test_connection(client)
        response = _remove_email_code(client)
    assert response.status_code == 400
    assert row.auth_methods == ["email_code", "oidc"]


def test_editing_the_provider_config_invalidates_the_test():
    for field, value in (
        ("oidc_issuer", ISSUER + "/realm"),
        ("oidc_client_id", "another-client"),
        ("oidc_client_secret", "another-secret"),
    ):
        row = _row()
        with admin_session(row) as client:
            _test_connection(client)
            edited = client.patch("/admin/settings", json={field: value})
            assert edited.status_code == 200, edited.text
            assert edited.json()["oidc_connection_test"] is None, field
            assert _remove_email_code(client).status_code == 400, field


def test_editing_the_config_and_removing_email_code_in_one_request_is_refused():
    row = _row()
    with admin_session(row) as client:
        _test_connection(client)
        response = client.patch(
            "/admin/settings",
            json={"auth_methods": ["oidc"], "oidc_client_id": "another-client"},
        )
    assert response.status_code == 400
    assert row.auth_methods == ["email_code", "oidc"]


def test_editing_something_else_keeps_the_test():
    row = _row()
    with admin_session(row) as client:
        _test_connection(client)
        client.patch("/admin/settings", json={"oidc_button_label": "SSO"})
        assert _remove_email_code(client).status_code == 200


def test_saving_the_same_secret_again_invalidates_the_test():
    row = _row(oidc_client_secret_encrypted=encrypt_secret("s").encode())
    with admin_session(row) as client:
        _test_connection(client)
        client.patch("/admin/settings", json={"oidc_client_secret": "s"})
        assert _remove_email_code(client).status_code == 400


def test_other_method_changes_never_need_a_test():
    row = _row()
    with admin_session(row) as client:
        # Adding or keeping email_code, or leaving the methods alone.
        assert (
            client.patch(
                "/admin/settings", json={"auth_methods": ["email_code", "oidc"]}
            ).status_code
            == 200
        )
        assert (
            client.patch(
                "/admin/settings", json={"auth_methods": ["email_code"]}
            ).status_code
            == 200
        )


def test_email_code_can_come_back_without_a_test():
    row = _row(auth_methods=["oidc"])
    with admin_session(row) as client:
        response = client.patch(
            "/admin/settings", json={"auth_methods": ["email_code", "oidc"]}
        )
    assert response.status_code == 200


def test_the_connection_test_is_for_admins_only():
    app = FastAPI()
    app.include_router(admin_router.router)
    response = TestClient(app).post("/admin/settings/oidc/test")
    assert response.status_code in (401, 403)


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
