"""Tests for the ReadinessRegistry + probe_server (Phase 2 of OAuth refactor)."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from backend.tool_arena.config import (
    ApiKeyAuth,
    MCPServerConfig,
    NoAuth,
    OAuth2Auth,
)
from backend.tool_arena.credential import (
    CredentialMisconfigured,
    CredentialRevoked,
    CredentialUpstreamDown,
    _clear_credential_cache,
)
from backend.tool_arena.readiness import (
    ReadinessRegistry,
    ServerReadiness,
    ServerStatus,
    _reset_registry_for_tests,
    get_readiness_registry,
    probe_server,
)

pytestmark = pytest.mark.anyio


@pytest.fixture(autouse=True)
def _isolate_caches():
    _clear_credential_cache()
    _reset_registry_for_tests()
    yield
    _clear_credential_cache()
    _reset_registry_for_tests()


def _none_server(server_id: str = "n") -> MCPServerConfig:
    return MCPServerConfig(
        id=server_id,
        name="None",
        description="t",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=NoAuth(type="none"),
    )


def _api_server(server_id: str = "k") -> MCPServerConfig:
    return MCPServerConfig(
        id=server_id,
        name="Api",
        description="t",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=ApiKeyAuth(type="api_key", key_env="MY_KEY"),
    )


def _oauth_server(server_id: str = "o") -> MCPServerConfig:
    return MCPServerConfig(
        id=server_id,
        name="OAuth",
        description="t",
        endpoint="https://example.com/mcp",
        transport="streamablehttp",
        auth=OAuth2Auth(
            type="oauth2",
            client_id="cid",
            client_secret_env="OAUTH_SECRET_ENV",
            token_url="https://example.com/token",
        ),
    )


# --------------------------------------------------------------------------- #
# Registry behaviour
# --------------------------------------------------------------------------- #


def test_get_returns_unknown_for_unprobed_server():
    reg = ReadinessRegistry()
    snap = reg.get("never-seen")
    assert isinstance(snap, ServerReadiness)
    assert snap.status == ServerStatus.UNKNOWN
    assert snap.last_checked_at is None
    assert snap.consecutive_failures == 0


def test_set_ready_records_status_and_resets_failure_counter():
    reg = ReadinessRegistry()
    reg.set_failed("s", ServerStatus.UPSTREAM_DOWN, "boom")
    reg.set_failed("s", ServerStatus.UPSTREAM_DOWN, "boom")
    assert reg.get("s").consecutive_failures == 2

    reg.set_ready("s")
    snap = reg.get("s")
    assert snap.status == ServerStatus.READY
    assert snap.consecutive_failures == 0
    assert snap.last_error is None
    assert snap.last_checked_at is not None


def test_set_failed_increments_consecutive_failures():
    reg = ReadinessRegistry()
    reg.set_failed("s", ServerStatus.UPSTREAM_DOWN, "boom-1")
    reg.set_failed("s", ServerStatus.UPSTREAM_DOWN, "boom-2")
    reg.set_failed("s", ServerStatus.NEEDS_REAUTH, "revoked")
    assert reg.get("s").consecutive_failures == 3
    assert reg.get("s").status == ServerStatus.NEEDS_REAUTH
    assert "revoked" in (reg.get("s").last_error or "")


def test_ready_servers_filters_correctly():
    reg = ReadinessRegistry()
    s1, s2, s3, s4 = (
        _none_server("a"),
        _none_server("b"),
        _none_server("c"),
        _none_server("d"),
    )
    reg.set_ready(s1.id)
    reg.set_failed(s2.id, ServerStatus.NEEDS_REAUTH, "x")
    reg.set_failed(s3.id, ServerStatus.MISCONFIGURED, "x")
    # s4 stays UNKNOWN

    ready = reg.ready_servers([s1, s2, s3, s4])
    assert [s.id for s in ready] == ["a"]


def test_unknown_is_not_ready():
    reg = ReadinessRegistry()
    s = _none_server("only")
    assert reg.ready_servers([s]) == []


def test_snapshot_returns_all_known_states():
    reg = ReadinessRegistry()
    reg.set_ready("a")
    reg.set_failed("b", ServerStatus.MISCONFIGURED, "missing env")
    snap = {r.server_id: r for r in reg.snapshot()}
    assert set(snap.keys()) == {"a", "b"}
    assert snap["a"].status == ServerStatus.READY
    assert snap["b"].status == ServerStatus.MISCONFIGURED


def test_to_dict_is_json_safe():
    reg = ReadinessRegistry()
    reg.set_failed("a", ServerStatus.UPSTREAM_DOWN, "boom")
    [d] = [r.to_dict() for r in reg.snapshot()]
    assert d["server_id"] == "a"
    assert d["status"] == "UPSTREAM_DOWN"
    assert d["consecutive_failures"] == 1
    assert isinstance(d["last_checked_at"], str)


# --------------------------------------------------------------------------- #
# probe_server — exception mapping
# --------------------------------------------------------------------------- #


async def test_probe_none_server_marks_ready():
    reg = ReadinessRegistry()
    server = _none_server("n1")
    result = await probe_server(server, reg)
    assert result.status == ServerStatus.READY
    assert reg.get("n1").status == ServerStatus.READY


async def test_probe_api_key_server_marks_ready_when_env_set(monkeypatch):
    monkeypatch.setenv("MY_KEY", "secret-abc")
    reg = ReadinessRegistry()
    server = _api_server("k1")
    result = await probe_server(server, reg)
    assert result.status == ServerStatus.READY


async def test_probe_api_key_server_misconfigured_when_env_missing(monkeypatch):
    monkeypatch.delenv("MY_KEY", raising=False)
    reg = ReadinessRegistry()
    server = _api_server("k1")
    result = await probe_server(server, reg)
    assert result.status == ServerStatus.MISCONFIGURED
    assert "CredentialMisconfigured" in (result.last_error or "")


async def test_probe_oauth_revoked_maps_to_needs_reauth():
    reg = ReadinessRegistry()
    server = _oauth_server("o1")

    async def fake_prewarm(_):
        raise CredentialRevoked("refresh token rejected")

    with patch(
        "backend.tool_arena.auth.prewarm_oauth_provider",
        side_effect=fake_prewarm,
    ):
        result = await probe_server(server, reg)

    assert result.status == ServerStatus.NEEDS_REAUTH
    assert "CredentialRevoked" in (result.last_error or "")


async def test_probe_oauth_misconfigured_maps_to_misconfigured():
    reg = ReadinessRegistry()
    server = _oauth_server("o1")

    async def fake_prewarm(_):
        raise CredentialMisconfigured("missing env")

    with patch(
        "backend.tool_arena.auth.prewarm_oauth_provider",
        side_effect=fake_prewarm,
    ):
        result = await probe_server(server, reg)

    assert result.status == ServerStatus.MISCONFIGURED


async def test_probe_oauth_upstream_down_maps_to_upstream_down():
    reg = ReadinessRegistry()
    server = _oauth_server("o1")

    async def fake_prewarm(_):
        raise CredentialUpstreamDown("token endpoint 502")

    with patch(
        "backend.tool_arena.auth.prewarm_oauth_provider",
        side_effect=fake_prewarm,
    ):
        result = await probe_server(server, reg)

    assert result.status == ServerStatus.UPSTREAM_DOWN


async def test_probe_oauth_prewarm_returns_false_marks_upstream_down():
    """prewarm_oauth_provider returns False on swallowed failures.

    The probe must translate that into UPSTREAM_DOWN — never silently READY.
    """
    reg = ReadinessRegistry()
    server = _oauth_server("o1")

    async def fake_prewarm(_):
        return False

    with patch(
        "backend.tool_arena.auth.prewarm_oauth_provider",
        side_effect=fake_prewarm,
    ):
        result = await probe_server(server, reg)

    assert result.status == ServerStatus.UPSTREAM_DOWN


async def test_probe_oauth_success_marks_ready():
    reg = ReadinessRegistry()
    server = _oauth_server("o1")

    async def fake_prewarm(_):
        return True

    with patch(
        "backend.tool_arena.auth.prewarm_oauth_provider",
        side_effect=fake_prewarm,
    ):
        result = await probe_server(server, reg)

    assert result.status == ServerStatus.READY


async def test_probe_timeout_maps_to_upstream_down():
    reg = ReadinessRegistry()
    server = _oauth_server("o1")

    async def slow_prewarm(_):
        await asyncio.sleep(5)
        return True

    with patch(
        "backend.tool_arena.auth.prewarm_oauth_provider",
        side_effect=slow_prewarm,
    ):
        result = await probe_server(server, reg, timeout_seconds=0.05)

    assert result.status == ServerStatus.UPSTREAM_DOWN


# --------------------------------------------------------------------------- #
# consecutive_failures lifecycle
# --------------------------------------------------------------------------- #


async def test_consecutive_failures_increments_on_repeated_failures(monkeypatch):
    monkeypatch.delenv("MY_KEY", raising=False)
    reg = ReadinessRegistry()
    server = _api_server("k1")

    await probe_server(server, reg)
    await probe_server(server, reg)
    await probe_server(server, reg)

    assert reg.get("k1").consecutive_failures == 3
    assert reg.get("k1").status == ServerStatus.MISCONFIGURED


async def test_consecutive_failures_resets_on_success(monkeypatch):
    reg = ReadinessRegistry()
    server = _api_server("k1")

    monkeypatch.delenv("MY_KEY", raising=False)
    await probe_server(server, reg)
    await probe_server(server, reg)
    assert reg.get("k1").consecutive_failures == 2

    monkeypatch.setenv("MY_KEY", "now-set")
    await probe_server(server, reg)
    assert reg.get("k1").status == ServerStatus.READY
    assert reg.get("k1").consecutive_failures == 0


# --------------------------------------------------------------------------- #
# Singleton accessor
# --------------------------------------------------------------------------- #


def test_get_readiness_registry_is_singleton():
    a = get_readiness_registry()
    b = get_readiness_registry()
    assert a is b
