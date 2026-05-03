"""MCPDispatcher — orchestrates concurrent MCP tool calls.

Single entry point: dispatch(task, goal, session_id) returns two MCPToolCall
objects with sanitized results. Each MCP server is responsible for producing
its own finished answer (full RAG: retrieval + generation, or agentic
synthesis). The dispatcher only routes, sanitizes, and returns.

Pipeline:
1. Pick two servers via registry.pick_two()
2. Call both MCP servers concurrently with timeout + failure isolation
3. Normalize and sanitize each server's output
4. Return tuple[MCPToolCall, MCPToolCall]
"""

import asyncio
import logging
import os

from backend.tool_arena.client import single_mcp_call
from backend.tool_arena.config import MCPServerConfig
from backend.tool_arena.models import MCPToolCall
from backend.tool_arena.normalizer import normalize_output
from backend.tool_arena.readiness import get_readiness_registry
from backend.tool_arena.registry import registry
from backend.tool_arena.sanitizer import sanitize_envelope, sanitize_output


class InsufficientReadyServersError(RuntimeError):
    """Raised when fewer than 2 MCP servers are in READY state.

    Surfaces as 503 ``tool_unavailable`` at the router layer. The dispatcher
    will not silently degrade by retrying with non-ready servers — once a
    server is filtered out by the readiness registry, the only way back in is
    a successful probe.
    """

    def __init__(self, ready_count: int, snapshot: list) -> None:
        super().__init__(
            f"Need at least 2 READY servers; have {ready_count}."
        )
        self.ready_count = ready_count
        self.snapshot = snapshot

logger = logging.getLogger("languia")

# Default MCP call timeout in seconds. Configurable globally via env var, and
# overridable per-server via MCPServerConfig.timeout_seconds. The previous 30s
# default was too aggressive for agentic tools (e.g. Clarifeye's call_agent
# does multi-step reasoning + internal LLM calls).
MCP_CALL_TIMEOUT = float(os.environ.get("MCP_CALL_TIMEOUT", "90"))

# Number of retry attempts on transient connection errors (NOT on timeout).
# A timeout retry would double the user's wait without adding signal; a
# connection retry recovers from network blips (e.g. brief Clarifeye 502).
MCP_CALL_RETRIES = int(os.environ.get("MCP_CALL_RETRIES", "1"))


class MCPDispatcher:
    """Orchestrates two concurrent MCP calls and returns sanitized results."""

    async def dispatch(
        self,
        task: str,
        goal: str,
        session_id: str,
        document_content: str = "",
    ) -> tuple[MCPToolCall, MCPToolCall]:
        """Run full comparison pipeline: pick servers, call MCP, sanitize, return.

        Args:
            task: User's task description (what to do).
            goal: User's goal description (what good looks like).
            session_id: Unique session identifier for this comparison.
            document_content: Optional uploaded document text.

        Returns:
            Tuple of two MCPToolCall objects, one per server.
        """
        # Filter the pool through the readiness registry. Servers in
        # NEEDS_REAUTH / MISCONFIGURED / UPSTREAM_DOWN / UNKNOWN are excluded.
        readiness = get_readiness_registry()
        all_servers = [registry.get_server(sid) for sid in registry.server_ids]
        ready = readiness.ready_servers(all_servers)
        if len(ready) < 2:
            snapshot = [r.to_dict() for r in readiness.snapshot()]
            logger.warning(
                "dispatcher: insufficient READY servers (have=%d, need=2). snapshot=%s",
                len(ready), snapshot,
            )
            raise InsufficientReadyServersError(len(ready), snapshot)

        # Mirror the registry.pick_two contract on the filtered subset: pick
        # two distinct READY servers at random, preserving their relative
        # order in the ready list (so callers and tests see a stable A/B
        # mapping when the pool is exactly 2).
        import random

        if len(ready) == 2:
            server_a, server_b = ready[0], ready[1]
        else:
            picked_indices = sorted(random.sample(range(len(ready)), 2))
            server_a, server_b = ready[picked_indices[0]], ready[picked_indices[1]]
        servers = [server_a, server_b]

        raw_results = await asyncio.gather(
            self._call_with_resilience(server_a, task, goal, document_content),
            self._call_with_resilience(server_b, task, goal, document_content),
            return_exceptions=True,
        )

        tool_calls: list[MCPToolCall] = []

        for server, result in zip(servers, raw_results):
            if isinstance(result, Exception):
                logger.error(
                    "MCP call to %s failed: %s: %s",
                    server.id,
                    type(result).__name__,
                    result,
                )
                tool_calls.append(
                    MCPToolCall(
                        session_id=session_id,
                        task=task,
                        goal=goal,
                        tool_id=server.id,
                        llm_id=server.llm_id or "",
                        raw_result="",
                        mediated_result="",
                        duration_ms=0,
                        error=f"{type(result).__name__}: {result}",
                    )
                )
            else:
                raw_text, duration_ms = result
                envelope = normalize_output(raw_text, duration_ms)
                envelope = sanitize_envelope(envelope, servers)
                sanitized = sanitize_output(envelope.answer, servers)
                tool_calls.append(
                    MCPToolCall(
                        session_id=session_id,
                        task=task,
                        goal=goal,
                        tool_id=server.id,
                        llm_id=server.llm_id or "",
                        raw_result=sanitized,
                        mediated_result=sanitized,
                        duration_ms=duration_ms,
                    )
                )

        return tool_calls[0], tool_calls[1]

    async def _call_with_resilience(
        self,
        server: MCPServerConfig,
        task: str,
        goal: str,
        document_content: str,
    ) -> tuple[str, int]:
        """Call a single MCP server with per-server timeout and bounded retry.

        - Timeout: server.timeout_seconds if set, else MCP_CALL_TIMEOUT.
        - Retry: up to MCP_CALL_RETRIES retries on transient connection errors
          (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadError).
        - NO retry on asyncio.TimeoutError — retrying after a timeout would
          double the user's wait without adding signal.
        """
        import httpx

        timeout = server.timeout_seconds or MCP_CALL_TIMEOUT
        transient_excs = (
            httpx.ConnectError,
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.WriteError,
        )

        last_exc: Exception | None = None
        for attempt in range(MCP_CALL_RETRIES + 1):
            try:
                return await asyncio.wait_for(
                    single_mcp_call(server, task, goal, document_content),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "mcp call timed out server=%s timeout_s=%.1f attempt=%d (no retry on timeout)",
                    server.id, timeout, attempt + 1,
                )
                raise
            except transient_excs as exc:
                last_exc = exc
                logger.warning(
                    "mcp call transient error server=%s attempt=%d/%d type=%s: %s",
                    server.id, attempt + 1, MCP_CALL_RETRIES + 1,
                    type(exc).__name__, exc,
                )
                if attempt >= MCP_CALL_RETRIES:
                    raise
                await asyncio.sleep(2 ** attempt)
        raise last_exc if last_exc else RuntimeError("unreachable")
