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
from backend.tool_arena.credential import (
    CredentialError,
    OAuth2Credential,
    credential_for,
)

logger = logging.getLogger("languia")


def _build_task_prompt(task: str, document_content: str) -> str:
    """Prepend a [CONTEXT] block to the task when document_content is provided.

    Returns the plain task string when document_content is empty or
    whitespace-only. This is the INJ-01 injection point — called once per
    single_mcp_call invocation. Both Tool A and Tool B call this function
    with the same document_content, guaranteeing byte-identical context
    (equifinality contract).
    """
    if not document_content.strip():
        return task
    return f"[CONTEXT]\n{document_content}\n[/CONTEXT]\n\n{task}"


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
    # Single dispatch seam: the credential decides what headers to send and,
    # for OAuth, exposes the SDK provider object via OAuth2Credential.
    # See backend/tool_arena/credential.py for the asymmetry rationale.
    credential = credential_for(server)
    try:
        headers = await credential.headers_for(server)
    except CredentialError:
        # Propagate to dispatcher; it already wraps generic exceptions into
        # MCPToolCall error rows. Phase 2 will branch on the specific
        # subclass to surface readiness state to the UI.
        raise

    auth = None
    if isinstance(credential, OAuth2Credential):
        auth = credential.provider_for(server)

    start = time.monotonic()
    async with streamablehttp_client(
        str(server.endpoint),
        headers=headers,
        auth=auth,
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            if server.tools == ["*"]:
                tools_result = await session.list_tools()
                tool_name = tools_result.tools[0].name
            else:
                tool_name = server.tools[0]

            if tool_name == "call_agent":
                message = f"Task: {task}\nGoal: {goal}"
                if document_content:
                    message += f"\n\nDocument:\n{document_content}"
                arguments = {"message": message, **server.tool_args}
            else:
                task_prompt = _build_task_prompt(task, document_content)
                arguments = {"task": task_prompt, "goal": goal, "document_content": document_content}
            result = await session.call_tool(tool_name, arguments=arguments)

            raw_text = "\n".join(
                c.text for c in result.content if isinstance(c, TextContent)
            )
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "mcp call server=%s tool=%s raw_len=%d duration_ms=%d",
                server.id, tool_name, len(raw_text), duration_ms,
            )
            return raw_text, duration_ms
