"""MCPDispatcher — orchestrates concurrent MCP tool calls with LLM mediation.

Single entry point for Phase 3: dispatch(task, goal, llm_id, session_id)
returns two MCPToolCall objects with sanitized, LLM-mediated results.

Pipeline per CONTEXT.md D-04 through D-15:
1. Pick two servers via registry.pick_two() (D-14)
2. Call both MCP servers concurrently with timeout + failure isolation (D-10, D-11, MCP-01)
3. Sanitize raw results BEFORE LLM mediation (D-08)
4. Mediate both results through the same LLM concurrently (D-04, D-05, MCP-03)
5. Sanitize mediated results AFTER LLM mediation (D-08 defense in depth)
6. Return tuple[MCPToolCall, MCPToolCall] (D-13, D-15)
"""

import asyncio
import logging
import os

import litellm

from backend.tool_arena.client import single_mcp_call
from backend.tool_arena.config import MCPServerConfig
from backend.tool_arena.models import MCPToolCall
from backend.tool_arena.normalizer import normalize_output
from backend.tool_arena.registry import registry
from backend.tool_arena.sanitizer import sanitize_envelope, sanitize_output

logger = logging.getLogger("languia")

# Per D-10: 30-second default, configurable via environment variable
MCP_CALL_TIMEOUT = float(os.environ.get("MCP_CALL_TIMEOUT", "30"))

# Mediation output budget. Without this, providers fall back to a low default
# (e.g. ~1024 on OpenRouter for Anthropic) and visibly truncate the answer.
MEDIATION_MAX_TOKENS = int(os.environ.get("MEDIATION_MAX_TOKENS", "4096"))

MEDIATION_PROMPT = """\
You are given the raw output from a RAG tool that retrieved relevant chunks from a document.
Synthesize the retrieved chunks into a clear, complete answer that directly addresses the task and goal.
Use as much of the retrieved content as needed — do not summarize or shorten relevant information.

Task: {task}
Goal: {goal}{document_section}
Retrieved chunks:
{raw_result}

Provide a clean, human-readable answer. Do not mention the tool, its name, or any technical identifiers."""


class MCPDispatcher:
    """Orchestrates two concurrent MCP calls and LLM mediation.

    Per D-13: Single public method dispatch().
    Per D-15: This is the single entry point for Phase 3.
    Per D-16: No imports from backend.arena.
    """

    async def dispatch(
        self,
        task: str,
        goal: str,
        llm_id: str,
        session_id: str,
        document_content: str = "",
    ) -> tuple[MCPToolCall, MCPToolCall]:
        """Run full comparison pipeline: pick servers, call MCP, sanitize, mediate, return.

        Per D-14: Calls registry.pick_two(), runs both MCP calls + LLM mediation concurrently.
        Per D-06: llm_id is provided by caller (Phase 3 router), not chosen by dispatcher.
        Per TASK-02: Same task and goal are passed to both MCP calls.

        Args:
            task: User's task description (what to do).
            goal: User's goal description (what good looks like).
            llm_id: litellm model string (e.g., "openrouter/anthropic/claude-sonnet-4").
            session_id: Unique session identifier for this comparison.

        Returns:
            Tuple of two MCPToolCall objects, one per server.
        """
        server_a, server_b = registry.pick_two()
        servers = [server_a, server_b]

        # Step 1: Concurrent MCP calls with timeout + failure isolation (D-10, D-11, MCP-01)
        # asyncio.gather with return_exceptions=True ensures one failure does not discard the other
        raw_results = await asyncio.gather(
            asyncio.wait_for(
                single_mcp_call(server_a, task, goal, document_content),
                timeout=MCP_CALL_TIMEOUT,
            ),
            asyncio.wait_for(
                single_mcp_call(server_b, task, goal, document_content),
                timeout=MCP_CALL_TIMEOUT,
            ),
            return_exceptions=True,
        )

        # Step 2: Build MCPToolCall objects from raw results — sanitize on success, error on failure
        tool_calls: list[MCPToolCall] = []
        raw_texts: list[str] = []

        for server, result in zip(servers, raw_results):
            if isinstance(result, Exception):
                # Per D-11: Failed tool gets error field, empty raw/mediated results
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
                        llm_id=llm_id,
                        raw_result="",
                        mediated_result="",
                        duration_ms=0,
                        error=f"{type(result).__name__}: {result}",
                    )
                )
                raw_texts.append("")
            else:
                raw_text, duration_ms = result
                # Step 3a: Normalize raw output to canonical envelope (Phase 14 D-06)
                envelope = normalize_output(raw_text, duration_ms)
                # Step 3b: Sanitize envelope — strip source URLs and per-server terms
                envelope = sanitize_envelope(envelope, servers)
                # Step 3c: Sanitize answer text for id/name/endpoint patterns
                sanitized_raw = sanitize_output(envelope.answer, servers)
                tool_calls.append(
                    MCPToolCall(
                        session_id=session_id,
                        task=task,
                        goal=goal,
                        tool_id=server.id,
                        llm_id=llm_id,
                        raw_result=sanitized_raw,
                        mediated_result="",  # filled after mediation
                        duration_ms=duration_ms,
                    )
                )
                raw_texts.append(sanitized_raw)

        # Step 4: Concurrent LLM mediation for successful calls (D-04, D-05, MCP-03)
        # Failed calls (error is set) are skipped — no LLM call wasted
        mediation_coros = []
        mediation_indices = []
        for i, tc in enumerate(tool_calls):
            if tc.error is None:
                mediation_coros.append(
                    self._mediate(raw_texts[i], task, goal, llm_id, document_content)
                )
                mediation_indices.append(i)

        if mediation_coros:
            mediation_results = await asyncio.gather(*mediation_coros, return_exceptions=True)
            for idx, med_result in zip(mediation_indices, mediation_results):
                if isinstance(med_result, Exception):
                    logger.error(
                        "LLM mediation failed for %s: %s: %s",
                        tool_calls[idx].tool_id,
                        type(med_result).__name__,
                        med_result,
                    )
                    # raw_result is preserved; only error is set
                    tool_calls[idx].error = (
                        f"LLM mediation failed: {type(med_result).__name__}: {med_result}"
                    )
                else:
                    # Step 5: Sanitize mediated result post-LLM (D-08 defense in depth)
                    tool_calls[idx].mediated_result = sanitize_output(med_result, servers)

        return tool_calls[0], tool_calls[1]

    async def _mediate(self, raw_result: str, task: str, goal: str, llm_id: str, document_content: str = "") -> str:
        """Mediate a single sanitized raw result through the LLM (D-04).

        Args:
            raw_result: Sanitized raw MCP output.
            task: User's task description.
            goal: User's goal description.
            llm_id: litellm model string.

        Returns:
            LLM-mediated human-readable answer.
        """
        doc_section = ""
        if document_content.strip():
            preview = document_content[:800] + ("..." if len(document_content) > 800 else "")
            doc_section = f"\nDocument (first 800 chars):\n{preview}"
        prompt = MEDIATION_PROMPT.format(task=task, goal=goal, document_section=doc_section, raw_result=raw_result)
        response = await litellm.acompletion(
            model=llm_id,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            timeout=30,
            max_tokens=MEDIATION_MAX_TOKENS,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        finish_reason = getattr(choice, "finish_reason", None)
        logger.info(
            "mediation model=%s raw_len=%d output_len=%d finish_reason=%s max_tokens=%d",
            llm_id,
            len(raw_result),
            len(content),
            finish_reason,
            MEDIATION_MAX_TOKENS,
        )
        if finish_reason == "length":
            logger.warning(
                "mediation truncated by max_tokens (model=%s) — bump MEDIATION_MAX_TOKENS",
                llm_id,
            )
        return content
