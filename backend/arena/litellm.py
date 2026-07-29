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

import httpx
import litellm

from backend.arena.tools import ToolResult, ToolSpec
from backend.config import (
    GLOBAL_TIMEOUT,
    MAX_TOOL_CALLS,
    ORDBOGEN_GLOBAL_TIMEOUT,
    ORDBOGEN_STREAM_TIMEOUT,
    STREAM_TIMEOUT,
    settings,
)
from backend.errors import ContextTooLongError
from utils.database.models.messages.llm import (
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

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_TOOL_MODELS_CACHE_SECONDS = 3_600

_openrouter_tool_models: set[str] | None = None
_openrouter_tool_models_expires_at = 0.0
_openrouter_tool_models_lock = asyncio.Lock()


async def _get_openrouter_tool_models() -> set[str] | None:
    """Return OpenRouter's current tool-capable model IDs, with a short cache."""
    global _openrouter_tool_models, _openrouter_tool_models_expires_at

    now = monotonic()
    if _openrouter_tool_models is not None and _openrouter_tool_models_expires_at > now:
        return _openrouter_tool_models

    async with _openrouter_tool_models_lock:
        now = monotonic()
        if (
            _openrouter_tool_models is not None
            and _openrouter_tool_models_expires_at > now
        ):
            return _openrouter_tool_models

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    OPENROUTER_MODELS_URL,
                    params={"supported_parameters": "tools"},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
            data = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(data, list):
                raise ValueError("OpenRouter model response has no data list")
            tool_models = {
                item["id"]
                for item in data
                if isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and "tools" in (item.get("supported_parameters") or [])
            }
            if not tool_models:
                raise ValueError("OpenRouter returned no tool-capable models")
        except Exception:
            if _openrouter_tool_models is not None:
                logger.warning(
                    "Could not refresh OpenRouter tool capabilities; using stale data"
                )
                return _openrouter_tool_models
            logger.warning("Could not load OpenRouter tool capabilities")
            return None

        _openrouter_tool_models = tool_models
        _openrouter_tool_models_expires_at = now + OPENROUTER_TOOL_MODELS_CACHE_SECONDS
        return tool_models


async def _supports_tools(model: str) -> bool:
    """Return whether tools should be offered for this LiteLLM endpoint."""
    try:
        if litellm.supports_function_calling(model=model):
            return True

        # LiteLLM's static catalogue can lag behind OpenRouter's rapidly
        # changing model list. OpenRouter documents `supported_parameters=tools`
        # as the authoritative per-model capability filter.
        if model.startswith("openrouter/"):
            tool_models = await _get_openrouter_tool_models()
            return bool(
                tool_models and model.removeprefix("openrouter/") in tool_models
            )
        return False
    except Exception:
        logger.warning("Could not determine tool support for '%s'", model)
        return False


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
    tools_available = bool(tools_by_name) and await _supports_tools(endpoint.model)
    if tools_by_name and not tools_available:
        logger.info(
            "Tools requested but model '%s' does not support tool calling",
            endpoint.model,
            extra={"request": request},
        )

    msg.created_at = datetime.now()
    msg.agent_trace = []
    tool_call_count = 0
    total_tokens = 0

    while True:
        call_kwargs = {
            **base_kwargs,
            "messages": api_messages,
        }
        if tools_available and tool_call_count < MAX_TOOL_CALLS:
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
            logger.error(
                "context_window_exceeded: %s: %s",
                endpoint.model,
                exc,
                extra={"request": request},
            )
            raise ContextTooLongError from exc
        except litellm.UnsupportedParamsError:
            if "tools" not in call_kwargs:
                raise
            logger.info(
                "Provider rejected tool calling for '%s'; retrying without tools",
                endpoint.model,
                extra={"request": request},
            )
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
            msg.agent_trace.append(
                AgentTraceToolCall(
                    tool_call_id=tool_call_id,
                    name=tool_name,
                    arguments_json=arguments_json,
                    arguments=parsed_arguments,
                )
            )
            # Let the UI display the request while the external call is running.
            yield msg

            tool_call_count += 1
            tool_started_at = monotonic()
            # Every call gets a reply, even a refusal: omitting one would make
            # the next request invalid.
            if tool_call_count > MAX_TOOL_CALLS:
                result = ToolResult.error("The tool call limit has been reached.")
            elif (tool := tools_by_name.get(tool_name)) is None:
                result = ToolResult.error(f"Unknown tool '{tool_name}'.")
            else:
                result = await tool.run(arguments_json)

            msg.agent_trace.append(
                AgentTraceToolResult(
                    tool_call_id=tool_call_id,
                    name=tool_name,
                    status=result.status,
                    duration_ms=max(0, int((monotonic() - tool_started_at) * 1_000)),
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

    msg.tokens = total_tokens or msg.tokens
    msg.updated_at = datetime.now()
    logger.debug(
        "Response stream ended for '%s' with generation_id='%s'",
        endpoint.model,
        msg.generation_id,
        extra={"request": request},
    )
    yield msg
