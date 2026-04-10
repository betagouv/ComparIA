"""MCP client wrapper for CompaRAG Tool Arena.

Provides single_mcp_call() coroutine that opens a fresh streamablehttp_client
session, discovers or calls specific tools, and returns raw text + duration.
"""

import logging
import time

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from backend.tool_arena.config import MCPServerConfig

logger = logging.getLogger("tool_arena")


async def single_mcp_call(
    server: MCPServerConfig,
    task: str,
    goal: str,
    document_content: str = "",
) -> tuple[str, int]:
    """Open a fresh MCP session, call tool(s), return (raw_text, duration_ms).

    Per D-03: Each call opens its own streamablehttp_client session.
    Per D-02: If server.tools is ["*"], discovers tools via list_tools().
              Otherwise calls the first named tool in server.tools.

    Args:
        server: MCP server configuration with endpoint, auth, and tool list.
        task: The task string from the user's task-goal pair.
        goal: The goal string from the user's task-goal pair.

    Returns:
        Tuple of (raw_text, duration_ms) where raw_text is the concatenated
        TextContent from the tool call result.

    Raises:
        mcp.McpError: On MCP protocol errors.
        ConnectionError: On network failures.
        Exception: On unexpected errors. Caller wraps in asyncio.wait_for.
    """
    headers: dict[str, str] = {}
    if server.auth and server.auth.token:
        headers["Authorization"] = f"Bearer {server.auth.token}"

    start = time.monotonic()
    async with streamablehttp_client(
        str(server.endpoint),
        headers=headers,
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if server.tools == ["*"]:
                tools_result = await session.list_tools()
                tool_name = tools_result.tools[0].name
            else:
                tool_name = server.tools[0]

            arguments = {"task": task, "goal": goal, "document_content": document_content}
            result = await session.call_tool(tool_name, arguments=arguments)

            raw_text = "\n".join(
                c.text for c in result.content if isinstance(c, TextContent)
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            return raw_text, duration_ms
