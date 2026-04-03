"""Tests for MCPDispatcher — concurrent MCP tool call orchestration with LLM mediation.

Covers:
- Concurrency: both MCP calls run via asyncio.gather
- Failure isolation: one failure does not corrupt the other result
- Sanitization order: raw -> sanitize -> LLM -> sanitize
- LLM mediation: same llm_id used for both results
- Task/goal identity: passed unchanged to both MCP calls
- Session/tool_id population in returned MCPToolCall objects
- Timeout configurable via MCP_CALL_TIMEOUT env var
- LLM mediation failure: raw_result preserved, error set
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from backend.tool_arena.config import MCPAuth, MCPServerConfig
from backend.tool_arena.models import MCPToolCall


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def server_a():
    return MCPServerConfig(
        id="server_a",
        name="Server A",
        description="test server A",
        endpoint="https://a.example.com/mcp",
        transport="streamablehttp",
        auth=MCPAuth(type="bearer", token="token_a"),
        tools=["*"],
    )


@pytest.fixture
def server_b():
    return MCPServerConfig(
        id="server_b",
        name="Server B",
        description="test server B",
        endpoint="https://b.example.com/mcp",
        transport="streamablehttp",
        auth=MCPAuth(type="bearer", token="token_b"),
        tools=["summarize"],
    )


def make_litellm_response(content: str) -> MagicMock:
    """Build a mock litellm ModelResponse-like object with the given content."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = content
    return mock_response


# ---------------------------------------------------------------------------
# Test 1: dispatch() returns a tuple of two MCPToolCall objects
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.anyio


async def test_dispatch_returns_two_tool_calls(server_a, server_b):
    """dispatch() should return exactly two MCPToolCall instances."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(
            return_value=make_litellm_response("mediated")
        )
        dispatcher = MCPDispatcher()
        result = await dispatcher.dispatch(
            task="test task",
            goal="test goal",
            llm_id="openai/gpt-4o",
            session_id="session-001",
        )

    assert isinstance(result, tuple)
    assert len(result) == 2
    call_a, call_b = result
    assert isinstance(call_a, MCPToolCall)
    assert isinstance(call_b, MCPToolCall)


# ---------------------------------------------------------------------------
# Test 2: dispatch() passes identical task and goal to both MCP calls (TASK-02)
# ---------------------------------------------------------------------------

async def test_dispatch_passes_identical_task_goal_to_both(server_a, server_b):
    """Both single_mcp_call invocations must receive the same task and goal."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    mock_mcp_call = AsyncMock(return_value=("raw output", 100))

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch("backend.tool_arena.dispatcher.single_mcp_call", mock_mcp_call),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(
            return_value=make_litellm_response("mediated")
        )
        dispatcher = MCPDispatcher()
        await dispatcher.dispatch(
            task="my task",
            goal="my goal",
            llm_id="openai/gpt-4o",
            session_id="session-002",
        )

    assert mock_mcp_call.call_count == 2
    calls = mock_mcp_call.call_args_list
    # Both calls must use same task and goal
    assert calls[0].args[1] == "my task"
    assert calls[0].args[2] == "my goal"
    assert calls[1].args[1] == "my task"
    assert calls[1].args[2] == "my goal"


# ---------------------------------------------------------------------------
# Test 3: dispatch() uses same llm_id for both litellm.acompletion calls (MCP-03)
# ---------------------------------------------------------------------------

async def test_dispatch_uses_same_llm_id_for_both_mediations(server_a, server_b):
    """Both litellm.acompletion calls must use the same llm_id."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    mock_acompletion = AsyncMock(return_value=make_litellm_response("mediated"))

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = mock_acompletion
        dispatcher = MCPDispatcher()
        await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openrouter/anthropic/claude-sonnet-4",
            session_id="session-003",
        )

    assert mock_acompletion.call_count == 2
    for c in mock_acompletion.call_args_list:
        assert c.kwargs["model"] == "openrouter/anthropic/claude-sonnet-4"


# ---------------------------------------------------------------------------
# Test 4: sanitize_output called on raw_result BEFORE litellm.acompletion (D-08)
# ---------------------------------------------------------------------------

async def test_sanitize_called_on_raw_before_llm(server_a, server_b):
    """sanitize_output must be called with the raw result BEFORE litellm.acompletion receives it."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    call_order = []

    def track_sanitize(text, servers):
        call_order.append(("sanitize", text))
        return f"[SANITIZED]{text}"

    async def track_acompletion(**kwargs):
        # Extract the content from messages to check what the LLM received
        content = kwargs["messages"][0]["content"]
        call_order.append(("llm", content))
        return make_litellm_response("llm output")

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw_text", 100),
        ),
        patch("backend.tool_arena.dispatcher.sanitize_output", side_effect=track_sanitize),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(side_effect=track_acompletion)
        dispatcher = MCPDispatcher()
        await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-004",
        )

    # sanitize must be called before any llm call
    sanitize_indices = [i for i, (name, _) in enumerate(call_order) if name == "sanitize"]
    llm_indices = [i for i, (name, _) in enumerate(call_order) if name == "llm"]

    # At least one pre-LLM sanitization call must occur before the first LLM call
    assert min(sanitize_indices) < min(llm_indices), (
        f"Expected sanitize before llm but order was: {call_order}"
    )

    # Verify LLM received sanitized text (containing [SANITIZED] prefix)
    llm_call_contents = [content for name, content in call_order if name == "llm"]
    assert any("[SANITIZED]raw_text" in c for c in llm_call_contents), (
        f"LLM did not receive sanitized text. LLM calls received: {llm_call_contents}"
    )


# ---------------------------------------------------------------------------
# Test 5: sanitize_output called on mediated_result AFTER litellm.acompletion (D-08 defense)
# ---------------------------------------------------------------------------

async def test_sanitize_called_on_mediated_after_llm(server_a, server_b):
    """sanitize_output must be called on the mediated result AFTER litellm.acompletion."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    sanitize_call_args = []

    def track_sanitize(text, servers):
        sanitize_call_args.append(text)
        return f"[SANITIZED]{text}"

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            new_callable=AsyncMock,
            return_value=("raw_text", 100),
        ),
        patch("backend.tool_arena.dispatcher.sanitize_output", side_effect=track_sanitize),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("llm_output"))
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-005",
        )

    # sanitize should have been called with "llm_output" at least once (post-LLM)
    assert "llm_output" in sanitize_call_args, (
        f"Expected sanitize_output called with 'llm_output' but calls were: {sanitize_call_args}"
    )

    # The mediated_result in the MCPToolCall should be the post-sanitized version
    assert result_a.mediated_result == "[SANITIZED]llm_output"
    assert result_b.mediated_result == "[SANITIZED]llm_output"


# ---------------------------------------------------------------------------
# Test 6: When one MCP call raises asyncio.TimeoutError, other still returns valid (MCP-04)
# ---------------------------------------------------------------------------

async def test_timeout_failure_isolation(server_a, server_b):
    """When one MCP call times out, the other MCPToolCall must still be populated."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    call_count = 0

    async def mcp_call_side_effect(server, task, goal):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ("raw output", 100)
        else:
            raise asyncio.TimeoutError()

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            side_effect=mcp_call_side_effect,
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated"))
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-006",
        )

    # One should succeed, one should have an error
    successful = [tc for tc in (result_a, result_b) if tc.error is None]
    failed = [tc for tc in (result_a, result_b) if tc.error is not None]

    assert len(successful) == 1, f"Expected 1 success but got: {[tc.error for tc in (result_a, result_b)]}"
    assert len(failed) == 1
    assert successful[0].mediated_result == "mediated"


# ---------------------------------------------------------------------------
# Test 7: When one MCP call raises mcp.McpError, failed MCPToolCall has error + empty results (D-11)
# ---------------------------------------------------------------------------

async def test_mcp_error_sets_error_field_and_empty_results(server_a, server_b):
    """Failed MCPToolCall must have error set and raw_result/mediated_result as empty strings."""
    import mcp
    from mcp.types import ErrorData

    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    call_count = 0

    async def mcp_call_side_effect(server, task, goal):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ("valid output", 200)
        else:
            raise mcp.McpError(ErrorData(code=-32600, message="protocol error"))

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            side_effect=mcp_call_side_effect,
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated"))
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-007",
        )

    failed = result_b  # second call fails
    assert failed.error is not None
    assert failed.raw_result == ""
    assert failed.mediated_result == ""


# ---------------------------------------------------------------------------
# Test 8: When one MCP call raises ConnectionError, the other result is unaffected (MCP-04)
# ---------------------------------------------------------------------------

async def test_connection_error_isolation(server_a, server_b):
    """ConnectionError on one server must not affect the other MCPToolCall."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    call_count = 0

    async def mcp_call_side_effect(server, task, goal):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("refused")
        return ("other server output", 120)

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            side_effect=mcp_call_side_effect,
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated B"))
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-008",
        )

    # First call fails
    assert result_a.error is not None
    assert result_a.raw_result == ""
    # Second call succeeds
    assert result_b.error is None
    assert result_b.mediated_result == "mediated B"


# ---------------------------------------------------------------------------
# Test 9: dispatch() calls registry.pick_two() to select servers (D-14)
# ---------------------------------------------------------------------------

async def test_dispatch_calls_registry_pick_two(server_a, server_b):
    """dispatch() must call registry.pick_two() exactly once."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated"))
        dispatcher = MCPDispatcher()
        await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-009",
        )

    mock_registry.pick_two.assert_called_once()


# ---------------------------------------------------------------------------
# Test 10: dispatch() populates MCPToolCall.tool_id with server.id for each result
# ---------------------------------------------------------------------------

async def test_dispatch_populates_tool_id(server_a, server_b):
    """Each MCPToolCall must have tool_id matching the server's id."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated"))
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-010",
        )

    assert result_a.tool_id == "server_a"
    assert result_b.tool_id == "server_b"


# ---------------------------------------------------------------------------
# Test 11: dispatch() populates MCPToolCall.session_id with the passed session_id
# ---------------------------------------------------------------------------

async def test_dispatch_populates_session_id(server_a, server_b):
    """MCPToolCall.session_id must match the session_id passed to dispatch()."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated"))
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="my-session-xyz",
        )

    assert result_a.session_id == "my-session-xyz"
    assert result_b.session_id == "my-session-xyz"


# ---------------------------------------------------------------------------
# Test 12: dispatch() reads MCP_CALL_TIMEOUT from environment (D-10), defaults to 30
# ---------------------------------------------------------------------------

async def test_dispatch_reads_timeout_from_env(server_a, server_b, monkeypatch):
    """MCP_CALL_TIMEOUT env var must control the timeout for asyncio.wait_for."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    monkeypatch.setenv("MCP_CALL_TIMEOUT", "15")

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
        patch("backend.tool_arena.dispatcher.asyncio.wait_for", side_effect=capture_wait_for),
    ):
        mock_litellm.acompletion = AsyncMock(return_value=make_litellm_response("mediated"))
        # Re-import to pick up monkeypatched env (module-level MCP_CALL_TIMEOUT)
        import importlib
        import backend.tool_arena.dispatcher as dispatcher_module
        importlib.reload(dispatcher_module)

        dispatcher = dispatcher_module.MCPDispatcher()
        await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-012",
        )

    # The timeout used should be 15.0 (from env)
    assert any(t == 15.0 for t in wait_for_timeouts), (
        f"Expected timeout 15.0 in wait_for calls but got: {wait_for_timeouts}"
    )


# ---------------------------------------------------------------------------
# Test 13: Failed MCP call skips LLM mediation
# ---------------------------------------------------------------------------

async def test_failed_mcp_call_skips_llm_mediation(server_a, server_b):
    """When one MCP call fails, litellm.acompletion must NOT be called for that result."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    call_count = 0

    async def mcp_call_side_effect(server, task, goal):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return ("valid output", 100)
        raise ConnectionError("down")

    mock_acompletion = AsyncMock(return_value=make_litellm_response("mediated"))

    with (
        patch("backend.tool_arena.dispatcher.registry", mock_registry),
        patch(
            "backend.tool_arena.dispatcher.single_mcp_call",
            side_effect=mcp_call_side_effect,
        ),
        patch(
            "backend.tool_arena.dispatcher.sanitize_output",
            side_effect=lambda text, servers: text,
        ),
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = mock_acompletion
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-013",
        )

    # Only ONE litellm call (for the successful server), not two
    assert mock_acompletion.call_count == 1, (
        f"Expected 1 LLM mediation call but got {mock_acompletion.call_count}"
    )
    assert result_b.error is not None


# ---------------------------------------------------------------------------
# Test 14: When litellm.acompletion raises, MCPToolCall gets error but raw_result preserved
# ---------------------------------------------------------------------------

async def test_llm_mediation_failure_preserves_raw_result(server_a, server_b):
    """If LLM mediation raises, the MCPToolCall.raw_result must be preserved and error set."""
    from backend.tool_arena.dispatcher import MCPDispatcher

    mock_registry = MagicMock()
    mock_registry.pick_two.return_value = (server_a, server_b)

    call_count = 0

    async def acompletion_side_effect(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return make_litellm_response("mediated A")
        raise RuntimeError("LLM is down")

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
        patch("backend.tool_arena.dispatcher.litellm") as mock_litellm,
    ):
        mock_litellm.acompletion = AsyncMock(side_effect=acompletion_side_effect)
        dispatcher = MCPDispatcher()
        result_a, result_b = await dispatcher.dispatch(
            task="task",
            goal="goal",
            llm_id="openai/gpt-4o",
            session_id="session-014",
        )

    # First mediation succeeds
    assert result_a.error is None
    assert result_a.mediated_result == "mediated A"
    # Second mediation fails — raw_result preserved, error set
    assert result_b.raw_result == "raw output"
    assert result_b.error is not None
    assert "LLM mediation failed" in result_b.error or "RuntimeError" in result_b.error
