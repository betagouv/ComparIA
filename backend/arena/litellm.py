"""
LiteLLM integration for unified API communication.

This module streams model responses and executes the tools it is given. It
knows nothing about what any particular tool does.
"""

import asyncio
import json
import logging
from datetime import datetime
from time import monotonic
from typing import TYPE_CHECKING, Any, AsyncGenerator, Union, cast

import litellm

from backend.arena.tools import (
    ToolResult,
    ToolSpec,
    model_rejects_tools,
    remember_tool_rejection,
)
from backend.config import (
    GLOBAL_TIMEOUT,
    MAX_TOOL_CALLS,
    MAX_TOOL_ROUNDS,
    ORDBOGEN_GLOBAL_TIMEOUT,
    ORDBOGEN_STREAM_TIMEOUT,
    STREAM_TIMEOUT,
    TOOL_TIME_BUDGET_SECONDS,
    settings,
)
from backend.errors import ContextTooLongError
from utils.database.models.messages.llm import (
    AgentStopReason,
    AgentTraceIntermediateContent,
    AgentTraceReasoning,
    AgentTraceToolCall,
    AgentTraceToolResult,
)

if TYPE_CHECKING:
    from fastapi import Request

    from backend.arena.conversation import AnyMessageRead
    from backend.llms.models import LLMDataEnabled
    from utils.database.models import LLMMessageCreate

logger = logging.getLogger("languia")

def _tool_arguments_for_trace(raw_arguments: Any) -> tuple[str, dict[str, Any] | None]:
    """Keep the exact provider arguments plus a parsed object when valid."""
    if isinstance(raw_arguments, str):
        arguments_json = raw_arguments
        try:
            parsed = json.loads(raw_arguments)
        except (json.JSONDecodeError, TypeError):
            return arguments_json, None
        return arguments_json, parsed if isinstance(parsed, dict) else None
    if isinstance(raw_arguments, dict):
        return json.dumps(raw_arguments, ensure_ascii=False), raw_arguments
    return json.dumps(raw_arguments, ensure_ascii=False), None


async def _refuse_tool_call(message: str) -> tuple[ToolResult, int]:
    """A reply for a call we decline to run, so the next request stays valid."""
    return ToolResult.error(message), 0


async def _run_tool_call(
    tool: ToolSpec | None,
    tool_name: str,
    arguments_json: str,
    seconds_left: float,
) -> tuple[ToolResult, int]:
    """
    Run one call and report how long it took.

    Every call gets a result, including the ones we refuse: omitting a reply to
    a tool call the model made would make the next request invalid.
    """
    started_at = monotonic()
    if tool is None:
        return ToolResult.error(f"Unknown tool '{tool_name}'."), 0
    if seconds_left <= 0:
        return ToolResult.error("The time budget for tools is exhausted."), 0
    try:
        async with asyncio.timeout(seconds_left):
            result = await tool.run(arguments_json)
    except TimeoutError:
        result = ToolResult.error("The tool call ran out of time.")
    except Exception:
        # A tool that raises is a broken tool, not a broken turn.
        logger.warning("Tool '%s' raised", tool_name)
        result = ToolResult.error("The tool failed. Continue without it.")
    return result, max(0, int((monotonic() - started_at) * 1_000))


def _shed_oldest_tool_round(api_messages: list[dict[str, Any]]) -> bool:
    """
    Drop the oldest assistant tool request together with its replies.

    A tool reply without its request is invalid, so the pair travels as a unit.
    Returns whether anything was shed.
    """
    for index, message in enumerate(api_messages):
        if message.get("role") == "assistant" and message.get("tool_calls"):
            end = index + 1
            while end < len(api_messages) and api_messages[end].get("role") == "tool":
                end += 1
            del api_messages[index:end]
            return True
    return False


def _message_from_built_response(response: Any) -> dict[str, Any]:
    """Extract the assistant message reconstructed by LiteLLM."""
    message = response.choices[0].message
    if hasattr(message, "model_dump"):
        # Keep provider-specific fields such as Gemini thought signatures. The
        # reconstructed LiteLLM message is intended to be sent back unchanged.
        data = message.model_dump(exclude_none=True)
    else:
        data = {
            key: getattr(message, key)
            for key in ("role", "content", "tool_calls")
            if getattr(message, key, None) is not None
        }
    return cast(dict[str, Any], data)


async def litellm_stream_iter(
    llm: "LLMDataEnabled",
    messages: list["AnyMessageRead"],
    msg: "LLMMessageCreate",
    temperature: float,
    max_new_tokens: int,
    request: Union["Request", None] = None,
    include_reasoning: bool = False,
    enable_reasoning: bool = False,
    tools: list[ToolSpec] | None = None,
) -> AsyncGenerator["LLMMessageCreate"]:
    """Stream a response, executing bounded model-requested tool calls."""
    endpoint = llm.litellm_endpoint

    logger.info(
        f"using endpoint {endpoint.model} for {llm.id}: "
        f"{endpoint.model_dump(mode='json', exclude={'api_key'})}",
        extra={"request": request},
    )

    if settings.SENTRY_DSN:
        litellm.input_callback = ["sentry"]
        litellm.failure_callback.append("sentry")

    is_ordbogen = bool(endpoint.base_url and "ordbogen.ai" in endpoint.base_url)
    api_messages: list[dict[str, Any]] = [
        message.model_dump(include={"role", "content"}, context={"merge_sources": True})
        for message in messages
    ]
    base_kwargs: dict[str, Any] = {
        "timeout": ORDBOGEN_GLOBAL_TIMEOUT if is_ordbogen else GLOBAL_TIMEOUT,
        "stream_timeout": ORDBOGEN_STREAM_TIMEOUT if is_ordbogen else STREAM_TIMEOUT,
        **endpoint.model_dump(),
        "temperature": temperature,
        "max_tokens": max_new_tokens,
        "stream": True,
    }

    if settings.MOCK_RESPONSE:
        logger.warning("MOCK_RESPONSE enabled")
        base_kwargs["mock_response"] = (
            "This is a fake response that didn't contact the LLM api."
        )
    if "c4ai-aya-expanse-32b" not in endpoint.model:
        base_kwargs["stream_options"] = {"include_usage": True}
    if include_reasoning:
        base_kwargs["include_reasoning"] = True
    if enable_reasoning:
        base_kwargs["enable_reasoning"] = True

    tools_by_name = {tool.name: tool for tool in tools or []}
    # Capability is never declared, only discovered: schemas go out unless this
    # endpoint has already refused them.
    tools_available = bool(tools_by_name) and not model_rejects_tools(endpoint.model)
    if tools_by_name and not tools_available:
        logger.info(
            "Tools not offered to '%s': it refused them before",
            endpoint.model,
            extra={"request": request},
        )

    msg.created_at = datetime.now()
    msg.agent_trace = []
    tool_call_count = 0
    tool_round_count = 0
    total_tokens = 0
    tools_were_offered = tools_available
    # Set the first time we refuse to offer tools again, so that "the model was
    # done" and "we stopped it" stay distinguishable.
    stopped_by: AgentStopReason | None = None
    deadline = monotonic() + TOOL_TIME_BUDGET_SECONDS

    while True:
        seconds_left = deadline - monotonic()
        if tools_available and stopped_by is None:
            if tool_call_count >= MAX_TOOL_CALLS:
                stopped_by = "call_limit"
            elif tool_round_count >= MAX_TOOL_ROUNDS:
                stopped_by = "round_limit"
            elif seconds_left <= 0:
                stopped_by = "deadline"

        call_kwargs = {
            **base_kwargs,
            "messages": api_messages,
        }
        # A model given no schemas cannot ask for a tool, so it has to answer.
        if tools_available and stopped_by is None:
            call_kwargs["tools"] = [tool.schema for tool in tools_by_name.values()]
            call_kwargs["tool_choice"] = "auto"

        chunks: list[Any] = []
        content_before_call = msg.content
        reasoning_before_call = msg.reasoning_content or ""

        try:
            response = await litellm.acompletion(**call_kwargs)
            async for chunk in response:
                chunks.append(chunk)
                if not msg.responded_at:
                    msg.responded_at = datetime.now()
                if not msg.generation_id and chunk.id:
                    msg.generation_id = chunk.id

                usage = getattr(chunk, "usage", None)
                completion_tokens = getattr(usage, "completion_tokens", None)
                if completion_tokens:
                    total_tokens += completion_tokens

                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                delta = choice.get("delta") or {}
                if content := delta.get("content"):
                    msg.content += content
                if reasoning := delta.get("reasoning_content") or delta.get(
                    "reasoning"
                ):
                    msg.reasoning_content = (msg.reasoning_content or "") + reasoning

                if msg.content or msg.reasoning_content:
                    yield msg
        except litellm.ContextWindowExceededError as exc:
            # Tool results are what usually blew the window. Shedding the oldest
            # round buys room; only a conversation with no tool traffic left to
            # shed is genuinely too long for this model.
            if _shed_oldest_tool_round(api_messages):
                logger.info(
                    "context_window_exceeded for '%s'; shed the oldest tool round",
                    endpoint.model,
                    extra={"request": request},
                )
                stopped_by = "context_exceeded"
                msg.content = content_before_call
                msg.reasoning_content = reasoning_before_call
                continue
            logger.error(
                "context_window_exceeded: %s: %s",
                endpoint.model,
                exc,
                extra={"request": request},
            )
            raise ContextTooLongError from exc
        except litellm.BadRequestError:
            # Providers disagree on how they refuse tools: some raise
            # UnsupportedParamsError, others a plain 400. Retrying without
            # schemas costs one request and tells us which it was -- an
            # unrelated 400 simply fails again, and that one reaches the caller.
            # ContextWindowExceededError is also a BadRequestError; it is caught
            # above, so it never reaches here.
            if "tools" not in call_kwargs:
                raise
            logger.info(
                "Provider rejected tool calling for '%s'; retrying without tools",
                endpoint.model,
                extra={"request": request},
            )
            remember_tool_rejection(endpoint.model)
            tools_available = False
            msg.content = content_before_call
            msg.reasoning_content = reasoning_before_call
            continue

        built_response = litellm.stream_chunk_builder(chunks, messages=api_messages)
        if built_response is None or not built_response.choices:
            break

        assistant_message = _message_from_built_response(built_response)
        tool_calls = assistant_message.get("tool_calls") or []
        if not tool_calls:
            round_reasoning = (msg.reasoning_content or "")[
                len(reasoning_before_call) :
            ]
            if round_reasoning:
                msg.agent_trace.append(AgentTraceReasoning(content=round_reasoning))
            # The final answer needs no trace event: it stays in msg.content.
            break

        round_reasoning = (msg.reasoning_content or "")[len(reasoning_before_call) :]
        round_content = msg.content[len(content_before_call) :]
        if round_reasoning:
            msg.agent_trace.append(AgentTraceReasoning(content=round_reasoning))
        if round_content:
            msg.agent_trace.append(AgentTraceIntermediateContent(content=round_content))

        # Content/reasoning generated while requesting a tool is intermediate,
        # not the final answer. The frontend receives full accumulated state, so
        # this update safely retracts any provider-emitted preamble.
        msg.content = content_before_call
        msg.reasoning_content = reasoning_before_call
        yield msg

        api_messages.append(assistant_message)
        tool_round_count += 1

        requested: list[tuple[str, str, str]] = []
        for raw_tool_call in tool_calls:
            tool_call = (
                raw_tool_call.model_dump(exclude_none=True)
                if hasattr(raw_tool_call, "model_dump")
                else raw_tool_call
            )
            function = tool_call.get("function") or {}
            tool_call_id = tool_call.get("id", "")
            tool_name = function.get("name", "")
            arguments_json, parsed_arguments = _tool_arguments_for_trace(
                function.get("arguments") or "{}"
            )
            requested.append((tool_call_id, tool_name, arguments_json))
            msg.agent_trace.append(
                AgentTraceToolCall(
                    tool_call_id=tool_call_id,
                    name=tool_name,
                    arguments_json=arguments_json,
                    arguments=parsed_arguments,
                )
            )
        # Show every request before any of them runs, so the UI reflects what the
        # model asked for while the external calls are in flight.
        yield msg

        seconds_left = deadline - monotonic()
        over_limit = tool_call_count + len(requested) > MAX_TOOL_CALLS
        tool_call_count += len(requested)

        pending = [
            _refuse_tool_call("The tool call limit has been reached.")
            if over_limit
            else _run_tool_call(
                tools_by_name.get(tool_name), tool_name, arguments_json, seconds_left
            )
            for _, tool_name, arguments_json in requested
        ]
        # Calls emitted together run together: running them in turn would spend
        # the whole budget on work that overlaps.
        outcomes = await asyncio.gather(*pending)

        for (tool_call_id, tool_name, _), (result, duration_ms) in zip(
            requested, outcomes
        ):
            msg.agent_trace.append(
                AgentTraceToolResult(
                    tool_call_id=tool_call_id,
                    name=tool_name,
                    status=result.status,
                    duration_ms=duration_ms,
                    content=result.content,
                    results=result.results,
                )
            )
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": result.content,
                }
            )
        # Surface every completed tool result, including empty/error states.
        yield msg

    if tools_were_offered:
        msg.agent_stop_reason = stopped_by or "completed"
    msg.tokens = total_tokens or msg.tokens
    msg.updated_at = datetime.now()
    logger.debug(
        "Response stream ended for '%s' with generation_id='%s'",
        endpoint.model,
        msg.generation_id,
        extra={"request": request},
    )
    yield msg
