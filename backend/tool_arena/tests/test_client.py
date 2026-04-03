"""Unit tests for the client module (single_mcp_call)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.tool_arena.config import MCPAuth, MCPServerConfig

pytestmark = pytest.mark.anyio


# --------------------------------------------------------------------------- #
# Helpers — build server configs
# --------------------------------------------------------------------------- #

def _make_server(tools: list[str] | None = None, with_auth: bool = True) -> MCPServerConfig:
    if tools is None:
        tools = ["*"]
    auth = MCPAuth(type="bearer", token="test_token_abc") if with_auth else None
    return MCPServerConfig(
        id="test_server",
        name="Test Server",
        description="test",
        endpoint="https://example.com/mcp/test",
        transport="streamablehttp",
        auth=auth,
        tools=tools,
    )


def _make_mock_session(tool_names: list[str], tool_output: str) -> MagicMock:
    """Build a mock ClientSession that returns the given tools and output."""
    from mcp.types import TextContent

    session = MagicMock()

    # Mock list_tools result
    list_tools_result = MagicMock()
    list_tools_result.tools = []
    for name in tool_names:
        mock_tool = MagicMock()
        mock_tool.name = name
        list_tools_result.tools.append(mock_tool)

    session.initialize = AsyncMock(return_value=None)
    session.list_tools = AsyncMock(return_value=list_tools_result)

    # Mock call_tool result using TextContent spec for isinstance check
    mock_content = MagicMock(spec=TextContent)
    mock_content.text = tool_output
    call_tool_result = MagicMock()
    call_tool_result.content = [mock_content]
    call_tool_result.isError = False
    session.call_tool = AsyncMock(return_value=call_tool_result)

    return session


def _make_stream_ctx(mock_session: MagicMock):
    """Return (streamablehttp ctx, ClientSession ctx) pair for patching."""
    ctx_manager = MagicMock()
    ctx_manager.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock(), MagicMock()))
    ctx_manager.__aexit__ = AsyncMock(return_value=None)

    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock(return_value=None)

    return ctx_manager, session_ctx


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

async def test_single_mcp_call_uses_list_tools_when_wildcard():
    """Test 1: single_mcp_call calls session.list_tools() when server.tools is ["*"]."""
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["*"])
    mock_session = _make_mock_session(["discovered_tool"], "result text")
    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    with patch("backend.tool_arena.client.streamablehttp_client", return_value=ctx_manager):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            raw_text, duration_ms = await single_mcp_call(server, "task text", "goal text")

    mock_session.list_tools.assert_awaited_once()
    mock_session.call_tool.assert_awaited_once_with(
        "discovered_tool", arguments={"task": "task text", "goal": "goal text"}
    )


async def test_single_mcp_call_uses_named_tool_when_not_wildcard():
    """Test 2: single_mcp_call calls the first named tool from server.tools when not ["*"]."""
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["extract_memo", "summarize"])
    mock_session = _make_mock_session(["extract_memo"], "memo output")
    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    with patch("backend.tool_arena.client.streamablehttp_client", return_value=ctx_manager):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            await single_mcp_call(server, "task text", "goal text")

    # Should NOT call list_tools when tools are explicitly named
    mock_session.list_tools.assert_not_awaited()
    mock_session.call_tool.assert_awaited_once_with(
        "extract_memo", arguments={"task": "task text", "goal": "goal text"}
    )


async def test_single_mcp_call_passes_task_and_goal_as_arguments():
    """Test 3: single_mcp_call passes {"task": task, "goal": goal} as arguments."""
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["my_tool"])
    mock_session = _make_mock_session(["my_tool"], "some output")
    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    with patch("backend.tool_arena.client.streamablehttp_client", return_value=ctx_manager):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            await single_mcp_call(server, "my specific task", "my specific goal")

    call_args = mock_session.call_tool.call_args
    assert call_args.kwargs["arguments"] == {
        "task": "my specific task",
        "goal": "my specific goal",
    }


async def test_single_mcp_call_returns_raw_text_and_duration():
    """Test 4: single_mcp_call returns (raw_text, duration_ms) from TextContent."""
    from mcp.types import TextContent
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["summary_tool"])
    mock_session = _make_mock_session(["summary_tool"], "")

    # Override with multiple text content items
    mock_content1 = MagicMock(spec=TextContent)
    mock_content1.text = "First line"
    mock_content2 = MagicMock(spec=TextContent)
    mock_content2.text = "Second line"
    mock_session.call_tool.return_value.content = [mock_content1, mock_content2]

    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    with patch("backend.tool_arena.client.streamablehttp_client", return_value=ctx_manager):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            raw_text, duration_ms = await single_mcp_call(server, "task", "goal")

    assert raw_text == "First line\nSecond line"
    assert isinstance(duration_ms, int)


async def test_single_mcp_call_sets_authorization_header_when_auth_token_present():
    """Test 5: single_mcp_call sets Authorization header when server.auth.token is present."""
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["tool"], with_auth=True)
    mock_session = _make_mock_session(["tool"], "output")
    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    captured_kwargs: dict = {}

    def mock_streamable(url, headers=None, **kwargs):
        captured_kwargs["headers"] = headers
        return ctx_manager

    with patch("backend.tool_arena.client.streamablehttp_client", side_effect=mock_streamable):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            await single_mcp_call(server, "task", "goal")

    assert captured_kwargs["headers"].get("Authorization") == "Bearer test_token_abc"


async def test_single_mcp_call_no_authorization_header_when_no_auth():
    """Test 6: single_mcp_call does NOT set Authorization header when server.auth is None."""
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["tool"], with_auth=False)
    mock_session = _make_mock_session(["tool"], "output")
    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    captured_kwargs: dict = {}

    def mock_streamable(url, headers=None, **kwargs):
        captured_kwargs["headers"] = headers
        return ctx_manager

    with patch("backend.tool_arena.client.streamablehttp_client", side_effect=mock_streamable):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            await single_mcp_call(server, "task", "goal")

    headers = captured_kwargs.get("headers", {})
    assert "Authorization" not in headers


async def test_single_mcp_call_raises_mcp_error_on_protocol_failure():
    """Test 7: single_mcp_call raises mcp.McpError when session.call_tool raises it."""
    import mcp
    from mcp.types import ErrorData
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["tool"])
    mock_session = MagicMock()
    mock_session.initialize = AsyncMock(return_value=None)
    mock_session.call_tool = AsyncMock(
        side_effect=mcp.McpError(ErrorData(code=-32600, message="protocol error"))
    )

    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    with patch("backend.tool_arena.client.streamablehttp_client", return_value=ctx_manager):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            with pytest.raises(mcp.McpError):
                await single_mcp_call(server, "task", "goal")


async def test_single_mcp_call_returns_non_negative_duration_ms():
    """Test 8: single_mcp_call returns duration_ms >= 0 (measured via time.monotonic)."""
    from backend.tool_arena.client import single_mcp_call

    server = _make_server(tools=["tool"])
    mock_session = _make_mock_session(["tool"], "output")
    ctx_manager, session_ctx = _make_stream_ctx(mock_session)

    with patch("backend.tool_arena.client.streamablehttp_client", return_value=ctx_manager):
        with patch("backend.tool_arena.client.ClientSession", return_value=session_ctx):
            raw_text, duration_ms = await single_mcp_call(server, "task", "goal")

    assert duration_ms >= 0
    assert isinstance(duration_ms, int)
