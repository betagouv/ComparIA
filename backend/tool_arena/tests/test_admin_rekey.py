"""Tests for ``POST /admin/tool-arena/oauth/seed`` (Phase 3)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.tool_arena.auth as auth_module
import backend.tool_arena.credential as credential_module
from backend.tool_arena.config import ApiKeyAuth, MCPServerConfig, OAuth2Auth
from backend.tool_arena.readiness import (
    ServerReadiness,
    ServerStatus,
    _reset_registry_for_tests,
)
from backend.tool_arena.router import admin_router

ADMIN_TOKEN = "test-admin-token"


def _make_oauth_server(server_id: str = "test_srv") -> MCPServerConfig:
    return MCPServerConfig(
        id=server_id,
        name="Test",
        description="t",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=OAuth2Auth(
            type="oauth2",
            client_id="cid",
            client_secret_env="TEST_SECRET",
            token_url="https://example.com/o/token/",
        ),
    )


def _make_apikey_server(server_id: str = "apikey_srv") -> MCPServerConfig:
    return MCPServerConfig(
        id=server_id,
        name="ApiKey",
        description="k",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=ApiKeyAuth(type="api_key", key_env="X_KEY", header="X-Key"),
    )


@pytest.fixture(autouse=True)
def _admin_token_env(monkeypatch):
    monkeypatch.setenv("ADMIN_STATUS_TOKEN", ADMIN_TOKEN)
    yield


@pytest.fixture(autouse=True)
def _reset_state():
    auth_module._clear_token_cache()
    credential_module._clear_credential_cache()
    _reset_registry_for_tests()
    yield
    auth_module._clear_token_cache()
    credential_module._clear_credential_cache()
    _reset_registry_for_tests()


@pytest.fixture
def app_with_server():
    """Yield (TestClient, set_active_server) so tests can register a stub server.

    Patches ``router.registry.get_server`` for the duration of the test only.
    """
    app = FastAPI()
    app.include_router(admin_router)
    state: dict[str, MCPServerConfig | None] = {"server": None}

    def _get(server_id: str) -> MCPServerConfig:
        srv = state["server"]
        if srv is not None and server_id == srv.id:
            return srv
        raise KeyError(server_id)

    with patch("backend.tool_arena.router.registry.get_server", side_effect=_get):
        client = TestClient(app)

        def set_server(srv: MCPServerConfig) -> None:
            state["server"] = srv

        yield client, set_server


def test_rekey_rejects_missing_bearer(app_with_server):
    client, set_server = app_with_server
    server = _make_oauth_server()
    set_server(server)
    resp = client.post(
        "/admin/tool-arena/oauth/seed",
        json={"server_id": server.id, "refresh_token": "rt"},
    )
    assert resp.status_code == 401


def test_rekey_rejects_wrong_bearer(app_with_server):
    client, set_server = app_with_server
    server = _make_oauth_server()
    set_server(server)
    resp = client.post(
        "/admin/tool-arena/oauth/seed",
        json={"server_id": server.id, "refresh_token": "rt"},
        headers={"Authorization": "Bearer nope"},
    )
    assert resp.status_code == 401


def test_rekey_404_for_unknown_server(app_with_server):
    client, set_server = app_with_server
    set_server(_make_oauth_server())
    resp = client.post(
        "/admin/tool-arena/oauth/seed",
        json={"server_id": "nope", "refresh_token": "rt"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 404


def test_rekey_400_for_non_oauth(app_with_server):
    client, set_server = app_with_server
    server = _make_apikey_server()
    set_server(server)
    resp = client.post(
        "/admin/tool-arena/oauth/seed",
        json={"server_id": server.id, "refresh_token": "rt"},
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 400


def test_rekey_happy_path_seeds_invalidates_caches_and_probes(app_with_server):
    client, set_server = app_with_server
    server = _make_oauth_server()
    set_server(server)

    # Pre-populate caches so we can observe invalidation.
    auth_module._provider_cache[server.id] = "stale-provider"  # type: ignore[assignment]
    credential_module._credential_cache[server.id] = "stale-cred"  # type: ignore[assignment]

    seed_calls: list[dict] = []

    async def _fake_seed_tokens(srv, **kwargs):
        seed_calls.append({"server_id": srv.id, **kwargs})

    async def _fake_probe(srv, registry, timeout_seconds: float = 10.0):
        return ServerReadiness(server_id=srv.id, status=ServerStatus.READY)

    with patch.object(auth_module, "seed_tokens", _fake_seed_tokens):
        with patch(
            "backend.tool_arena.router.probe_server",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            resp = client.post(
                "/admin/tool-arena/oauth/seed",
                json={
                    "server_id": server.id,
                    "refresh_token": "fresh_rt",
                    "access_token": "fresh_at",
                    "expires_in": 3600,
                },
                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["server_id"] == server.id
    assert body["readiness"]["status"] == "READY"
    assert "seeded_at" in body

    assert seed_calls == [{
        "server_id": server.id,
        "refresh_token": "fresh_rt",
        "access_token": "fresh_at",
        "expires_in": 3600,
    }]

    assert server.id not in auth_module._provider_cache
    assert server.id not in credential_module._credential_cache


def test_rekey_idempotent_second_call_succeeds(app_with_server):
    client, set_server = app_with_server
    server = _make_oauth_server()
    set_server(server)

    async def _fake_seed_tokens(srv, **kwargs):
        return None

    async def _fake_probe(srv, registry, timeout_seconds: float = 10.0):
        return ServerReadiness(server_id=srv.id, status=ServerStatus.READY)

    with patch.object(auth_module, "seed_tokens", _fake_seed_tokens):
        with patch(
            "backend.tool_arena.router.probe_server",
            new=AsyncMock(side_effect=_fake_probe),
        ):
            payload = {"server_id": server.id, "refresh_token": "rt"}
            headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}
            r1 = client.post("/admin/tool-arena/oauth/seed", json=payload, headers=headers)
            r2 = client.post("/admin/tool-arena/oauth/seed", json=payload, headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
