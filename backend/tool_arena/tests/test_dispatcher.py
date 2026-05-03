"""Tests for MCPDispatcher — concurrent MCP tool call orchestration.

Each MCP server returns a finished answer (full RAG pipeline). The dispatcher
only routes, sanitizes, and aggregates — there is no post-hoc LLM mediation.

Covers:
- Concurrency: both MCP calls run via asyncio.gather
- Failure isolation: one failure does not corrupt the other result
- Sanitization is applied to each successful result
- Task/goal identity: passed unchanged to both MCP calls
- Session/tool_id/llm_id population in returned MCPToolCall objects
- Timeout configurable via MCP_CALL_TIMEOUT env var, overridable per server
- Retry on transient connection errors, no retry on timeout
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.tool_arena.config import ApiKeyAuth, MCPServerConfig
from backend.tool_arena.models import MCPToolCall
from backend.tool_arena.readiness import (
    _reset_registry_for_tests,
    get_readiness_registry,
)


@pytest.fixture(autouse=True)
def _reset_readiness_between_tests():
    """Phase 2 introduced a process-local ReadinessRegistry. Reset between
    tests so seeded READY state from one test does not leak into the next."""
    _reset_registry_for_tests()
    yield
    _reset_registry_for_tests()


def _wire_registry_mock(mock_registry, *servers):
    """Configure a MagicMock registry to look like ``MCPRegistry``.

    The dispatcher now reads the full server pool via ``server_ids`` and
    ``get_server`` so it can filter through the readiness registry. The
    pre-Phase-2 contract (``pick_two``) is no longer used by the dispatcher
    but we preserve the mock's return for any test that still asserts on it.
    """
    by_id = {s.id: s for s in servers}
    mock_registry.server_ids = list(by_id.keys())
    mock_registry.get_server.side_effect = lambda sid: by_id[sid]
    mock_registry.pick_two.return_value = servers[:2]


def _mark_all_ready(*servers):
    reg = get_readiness_registry()
    for s in servers:
        reg.set_ready(s.id)


@pytest.fixture
def server_a():
    return MCPServerConfig(
        id="server_a",
        name="Server A",
        description="test server A",
        endpoint="https://a.example.com/mcp",
        transport="streamablehttp",
        auth=ApiKeyAuth(type="api_key", key_env="TEST_KEY_A", header="Authorization"),
        tools=["*"],
        llm_id="openrouter/mistralai/mistral-small-3.1-24b-instruct",
    )


@pytest.fixture
def server_b():
    return MCPServerConfig(
        id="server_b",
        name="Server B",
        description="test server B",
        endpoint="https://b.example.com/mcp",
        transport="streamablehttp",
        auth=ApiKeyAuth(type="api_key", key_env="TEST_KEY_B", header="Authorization"),
        tools=["summarize"],
        llm_id="openrouter/mistralai/mistral-small-3.1-24b-instruct",
    )


pytestmark = pytest.mark.anyio


def _patch_dispatch_basics(mock_registry, *, mcp_return=("raw output", 100), mcp_side_effect=None):
    """Common patches for dispatcher tests."""
    mcp_kwargs = {"side_effect": mcp_side_effect} if mcp_side_effect else {
        "new_callable": AsyncMock,
        "return_value": mcp_return,
    }
    return (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", **mcp_kwargs),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    )


async def test_dispatch_returns_two_tool_calls(server_a, server_b):
    """dispatch() returns exactly two MCPToolCall instances."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 150),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result = await MCPDispatcher().dispatch(
            task="test task", goal="test goal", session_id="session-001",
        )

    assert isinstance(result, tuple) and len(result) == 2
    call_a, call_b = result
    assert isinstance(call_a, MCPToolCall) and isinstance(call_b, MCPToolCall)


async def test_dispatch_passes_identical_task_goal_to_both(server_a, server_b):
    """Both single_mcp_call invocations must receive the same task and goal."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    mock_mcp_call = AsyncMock(return_value=("raw output", 100))

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", mock_mcp_call),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        await MCPDispatcher().dispatch(task="my task", goal="my goal", session_id="s")

    assert mock_mcp_call.call_count == 2
    for c in mock_mcp_call.call_args_list:
        assert c.args[1] == "my task"
        assert c.args[2] == "my goal"


async def test_sanitize_called_on_each_result(server_a, server_b):
    """sanitize_output must be called on each successful raw result."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    seen: list[str] = []

    def track_sanitize(text, servers):
        seen.append(text)
        return f"[SANITIZED]{text}"

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw_text", 100),
        ),
        patch("backend.tool_arena.dispatcher.sanitize_output", side_effect=track_sanitize),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="session-005",
        )

    assert result_a.mediated_result == "[SANITIZED]raw_text"
    assert result_b.mediated_result == "[SANITIZED]raw_text"
    assert result_a.raw_result == "[SANITIZED]raw_text"


async def test_timeout_failure_isolation(server_a, server_b):
    """When one MCP call times out, the other MCPToolCall must still be populated."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    call_count = 0

    async def mcp_call_side_effect(server, task, goal, document_content=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ("raw output", 100)
        raise asyncio.TimeoutError()

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", side_effect=mcp_call_side_effect),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="session-006",
        )

    successful = [tc for tc in (result_a, result_b) if tc.error is None]
    failed = [tc for tc in (result_a, result_b) if tc.error is not None]
    assert len(successful) == 1
    assert len(failed) == 1
    assert successful[0].mediated_result == "raw output"


async def test_mcp_error_sets_error_field_and_empty_results(server_a, server_b):
    """Failed MCPToolCall must have error set and raw_result/mediated_result as empty strings."""
    import mcp
    from mcp.types import ErrorData

    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    call_count = 0

    async def mcp_call_side_effect(server, task, goal, document_content=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ("valid output", 200)
        raise mcp.McpError(ErrorData(code=-32600, message="protocol error"))

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", side_effect=mcp_call_side_effect),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="session-007",
        )

    failed = result_b
    assert failed.error is not None
    assert failed.raw_result == ""
    assert failed.mediated_result == ""


async def test_connection_error_isolation(server_a, server_b):
    """ConnectionError on one server must not affect the other MCPToolCall."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    call_count = 0

    async def mcp_call_side_effect(server, task, goal, document_content=""):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("refused")
        return ("other server output", 120)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", side_effect=mcp_call_side_effect),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="session-008",
        )

    assert result_a.error is not None
    assert result_a.raw_result == ""
    assert result_b.error is None
    assert result_b.mediated_result == "other server output"


async def test_dispatch_consults_readiness_registry(server_a, server_b):
    """dispatch() must read the server pool via server_ids/get_server.

    Phase 2 replaced the direct ``registry.pick_two()`` call with a
    readiness-filtered random pick, so we now assert on the pool-fetch
    contract rather than on pick_two.
    """
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        await MCPDispatcher().dispatch(task="task", goal="goal", session_id="session-009")

    # ``server_ids`` is a list attribute (not a callable) on the real
    # registry, but ``get_server`` is called once per id.
    assert mock_registry.get_server.call_count == 2


async def test_dispatch_populates_tool_id(server_a, server_b):
    """Each MCPToolCall must have tool_id matching the server's id."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="session-010",
        )

    assert result_a.tool_id == "server_a"
    assert result_b.tool_id == "server_b"


async def test_dispatch_populates_session_id(server_a, server_b):
    """MCPToolCall.session_id must match the session_id passed to dispatch()."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="my-session-xyz",
        )

    assert result_a.session_id == "my-session-xyz"
    assert result_b.session_id == "my-session-xyz"


async def test_dispatch_populates_llm_id_from_server_config(server_a, server_b):
    """MCPToolCall.llm_id must be sourced from MCPServerConfig.llm_id, not a global."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    server_a_custom = server_a.model_copy(update={"llm_id": "openrouter/test/model-a"})
    server_b_no_llm = server_b.model_copy(update={"llm_id": None})

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a_custom, server_b_no_llm)

    _wire_registry_mock(mock_registry, server_a_custom, server_b_no_llm)
    _mark_all_ready(server_a_custom, server_b_no_llm)
    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="t", goal="g", session_id="s",
        )

    assert result_a.llm_id == "openrouter/test/model-a"
    assert result_b.llm_id == ""  # None -> "" for DB compat


async def test_dispatch_reads_timeout_from_env(server_a, server_b, monkeypatch):
    """MCP_CALL_TIMEOUT env var must control the timeout for asyncio.wait_for."""
    monkeypatch.setenv("MCP_CALL_TIMEOUT", "15")

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    # The reload inside the patch context replaces dispatcher.registry with
    # the real one (whose IDs come from mcp_servers.json). Pre-mark those as
    # READY so the readiness gate does not short-circuit the test before
    # asyncio.wait_for is exercised.
    from backend.tool_arena.registry import registry as _real_registry
    for _sid in _real_registry.server_ids:
        get_readiness_registry().set_ready(_sid)
    wait_for_timeouts = []
    original_wait_for = asyncio.wait_for

    async def capture_wait_for(coro, timeout):
        wait_for_timeouts.append(timeout)
        return await original_wait_for(coro, timeout)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.asyncio.wait_for", side_effect=capture_wait_for),
    ):
        import importlib

        import backend.tool_arena.dispatcher as dispatcher_module
        importlib.reload(dispatcher_module)

        await dispatcher_module.MCPDispatcher().dispatch(
            task="task", goal="goal", session_id="session-012",
        )

    assert any(t == 15.0 for t in wait_for_timeouts)


async def test_dispatch_uses_per_server_timeout(server_a, server_b):
    """server.timeout_seconds must override the global MCP_CALL_TIMEOUT."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    server_a_custom = server_a.model_copy(update={"timeout_seconds": 5.0})
    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a_custom, server_b)

    _wire_registry_mock(mock_registry, server_a_custom, server_b)
    _mark_all_ready(server_a_custom, server_b)
    captured_timeouts: list[float] = []
    original_wait_for = asyncio.wait_for

    async def capture_wait_for(coro, timeout):
        captured_timeouts.append(timeout)
        return await original_wait_for(coro, timeout)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw", 10),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.asyncio.wait_for", side_effect=capture_wait_for),
    ):
        await MCPDispatcher().dispatch(task="t", goal="g", session_id="s")

    assert 5.0 in captured_timeouts
    assert any(t != 5.0 for t in captured_timeouts)


async def test_dispatch_retries_on_transient_connection_error(server_a, server_b):
    """A single httpx.ConnectError must trigger one retry, then succeed."""
    import httpx

    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)
    call_count = {"n": 0}

    async def flaky_call(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.ConnectError("simulated network blip")
        return ("raw", 10)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", side_effect=flaky_call),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.asyncio.sleep", new_callable=AsyncMock),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="t", goal="g", session_id="s",
        )

    assert call_count["n"] == 3
    assert result_a.error is None
    assert result_b.error is None


async def test_dispatch_does_not_retry_on_timeout(server_a, server_b):
    """asyncio.TimeoutError must NOT trigger a retry — would double the wait."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    call_count = {"n": 0}

    async def slow_call(*args, **kwargs):
        call_count["n"] += 1
        await asyncio.sleep(10)
        return ("raw", 10)

    server_a_short = server_a.model_copy(update={"timeout_seconds": 0.05})
    server_b_short = server_b.model_copy(update={"timeout_seconds": 0.05})
    mock_registry.pick_two.return_value = (server_a_short, server_b_short)

    _wire_registry_mock(mock_registry, server_a_short, server_b_short)
    _mark_all_ready(server_a_short, server_b_short)
    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", side_effect=slow_call),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="t", goal="g", session_id="s",
        )

    assert call_count["n"] == 2
    assert result_a.error is not None
    assert result_b.error is not None


# --------------------------------------------------------------------------- #
# Phase 2: readiness gating
# --------------------------------------------------------------------------- #


async def test_dispatch_raises_when_all_servers_needs_reauth(server_a, server_b):
    """When every server is NEEDS_REAUTH the dispatcher must raise."""
    from backend.tool_arena.dispatcher import (
        InsufficientReadyServersError,
        MCPDispatcher,
    )
    from backend.tool_arena.readiness import ServerStatus

    mock_registry = MagicMock()
    _wire_registry_mock(mock_registry, server_a, server_b)
    reg = get_readiness_registry()
    reg.set_failed(server_a.id, ServerStatus.NEEDS_REAUTH, "ClassA: revoked")
    reg.set_failed(server_b.id, ServerStatus.NEEDS_REAUTH, "ClassB: revoked")

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
    ):
        with pytest.raises(InsufficientReadyServersError) as excinfo:
            await MCPDispatcher().dispatch(task="t", goal="g", session_id="s")

    assert excinfo.value.ready_count == 0


async def test_dispatch_raises_when_only_one_server_ready(server_a, server_b):
    """Need at least 2 READY servers — one is not enough."""
    from backend.tool_arena.dispatcher import (
        InsufficientReadyServersError,
        MCPDispatcher,
    )
    from backend.tool_arena.readiness import ServerStatus

    mock_registry = MagicMock()
    _wire_registry_mock(mock_registry, server_a, server_b)
    reg = get_readiness_registry()
    reg.set_ready(server_a.id)
    reg.set_failed(server_b.id, ServerStatus.UPSTREAM_DOWN, "Down: 502")

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
    ):
        with pytest.raises(InsufficientReadyServersError) as excinfo:
            await MCPDispatcher().dispatch(task="t", goal="g", session_id="s")

    assert excinfo.value.ready_count == 1


async def test_dispatch_proceeds_when_two_or_more_ready(server_a, server_b):
    """When >=2 servers are READY normal dispatch must proceed."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    _wire_registry_mock(mock_registry, server_a, server_b)
    _mark_all_ready(server_a, server_b)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw output", 100),
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        result_a, result_b = await MCPDispatcher().dispatch(
            task="t", goal="g", session_id="s",
        )

    assert result_a.error is None
    assert result_b.error is None


async def test_dispatch_excludes_unready_from_pool(server_a, server_b):
    """A 3-server pool with one MISCONFIGURED yields a 2-server ready pool."""
    from backend.tool_arena.dispatcher import MCPDispatcher
    from backend.tool_arena.readiness import ServerStatus

    server_c = server_a.model_copy(update={"id": "server_c", "name": "Server C"})

    mock_registry = MagicMock()
    _wire_registry_mock(mock_registry, server_a, server_b, server_c)
    reg = get_readiness_registry()
    reg.set_ready(server_a.id)
    reg.set_ready(server_b.id)
    reg.set_failed(server_c.id, ServerStatus.MISCONFIGURED, "missing env")

    seen_ids: set[str] = set()

    async def track(server, task, goal, document_content=""):
        seen_ids.add(server.id)
        return ("raw", 10)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", side_effect=track),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
    ):
        await MCPDispatcher().dispatch(task="t", goal="g", session_id="s")

    assert "server_c" not in seen_ids
    assert seen_ids.issubset({"server_a", "server_b"})
