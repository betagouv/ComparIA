"""Focused tests for model-directed Linkup web search."""

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, patch

import litellm
from linkup import LinkupSearchTextResult
from pydantic import BaseModel

from backend.arena import litellm as integration
from backend.arena import tools, web_search
from backend.arena.tools import resolve_builtin_tools
from utils.database.models import (
    AgentTraceToolCall,
    AgentTraceToolResult,
    LLMMessageCreate,
)


class FakeRedis:
    """Stands in for Redis so tests never touch a server."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value


def _web_search_tools():
    """Resolve web search the way the arena does when the user enables it."""
    return resolve_builtin_tools(["web_search"])


def _trace_sources(message: LLMMessageCreate) -> list[LinkupSearchTextResult]:
    """Sources the message received, as recorded in its trace."""
    return [
        result
        for event in message.agent_trace or []
        if event.type == "tool_result"
        for result in event.results
    ]


class UserMessage(BaseModel):
    role: str = "user"
    content: str


class AsyncChunkStream:
    def __init__(self, chunks: list[litellm.ModelResponse]) -> None:
        self._chunks = chunks

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        for chunk in self._chunks:
            yield chunk


def _chunk(
    *,
    response_id: str,
    delta: dict[str, Any] | None = None,
    finish_reason: str | None = None,
    usage: dict[str, int] | None = None,
) -> litellm.ModelResponse:
    choices = (
        [
            {
                "index": 0,
                "delta": delta or {},
                "finish_reason": finish_reason,
            }
        ]
        if delta is not None
        else []
    )
    return litellm.ModelResponse(
        id=response_id,
        model="test-model",
        stream=True,
        choices=choices,
        usage=usage,
    )


def _llm(model: str = "openrouter/anthropic/claude-sonnet-4.5") -> SimpleNamespace:
    endpoint = SimpleNamespace(
        model=model,
        base_url="https://example.invalid",
        model_dump=lambda **_: {
            "model": model,
            "api_key": "test-key",
            "base_url": "https://example.invalid",
            "api_version": None,
        },
    )
    return SimpleNamespace(id="test", litellm_endpoint=endpoint)


def test_model_can_search_then_stream_final_answer():
    asyncio.run(_test_model_can_search_then_stream_final_answer())


async def _test_model_can_search_then_stream_final_answer():
    calls: list[dict[str, Any]] = []
    responses = [
        AsyncChunkStream(
            [
                _chunk(
                    response_id="tool-round",
                    delta={
                        "role": "assistant",
                        "reasoning_content": "I need current information.",
                    },
                ),
                _chunk(
                    response_id="tool-round",
                    delta={"content": "I will check the web."},
                ),
                _chunk(
                    response_id="tool-round",
                    delta={
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "web_search",
                                    "arguments": '{"query":"latest public news"}',
                                },
                            }
                        ],
                    },
                    finish_reason="tool_calls",
                ),
                _chunk(
                    response_id="tool-round",
                    delta=None,
                    usage={
                        "prompt_tokens": 5,
                        "completion_tokens": 2,
                        "total_tokens": 7,
                    },
                ),
            ]
        ),
        AsyncChunkStream(
            [
                _chunk(
                    response_id="final-round",
                    delta={
                        "role": "assistant",
                        "reasoning_content": "The sources answer the question.",
                    },
                ),
                _chunk(
                    response_id="final-round",
                    delta={"content": "Current "},
                ),
                _chunk(
                    response_id="final-round",
                    delta={"content": "answer."},
                    finish_reason="stop",
                ),
                _chunk(
                    response_id="final-round",
                    delta=None,
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 3,
                        "total_tokens": 13,
                    },
                ),
            ]
        ),
    ]

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    result = LinkupSearchTextResult(
        type="text",
        name="Example",
        url="https://example.com/news",
        content="Fresh information",
    )

    async def fake_search(query: str, raise_on_error: bool = False):
        assert query == "latest public news"
        assert raise_on_error is True
        return [result]

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(web_search, "search_web", fake_search),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        message = LLMMessageCreate()
        streamed = [
            (item.content, len(_trace_sources(item)))
            async for item in integration.litellm_stream_iter(
                llm=_llm(),
                messages=[UserMessage(content="What happened?")],
                msg=message,
                temperature=0.7,
                max_new_tokens=100,
                tools=_web_search_tools(),
            )
        ]

    assert ("", 1) in streamed
    assert streamed[-1] == ("Current answer.", 1)
    assert message.tokens == 5
    assert _trace_sources(message) == [result]
    assert [event.type for event in message.agent_trace or []] == [
        "reasoning",
        "intermediate_content",
        "tool_call",
        "tool_result",
        "reasoning",
    ]
    assert message.agent_trace[2].arguments == {"query": "latest public news"}
    assert message.agent_trace[3].results == [result]
    assert calls[0]["tool_choice"] == "auto"
    assert calls[0]["tools"] == [web_search.WEB_SEARCH_TOOL_SCHEMA]
    assert calls[1]["messages"][-1]["role"] == "tool"
    assert "Fresh information" in calls[1]["messages"][-1]["content"]


def test_disabled_search_does_not_expose_tools():
    asyncio.run(_test_disabled_search_does_not_expose_tools())


def test_tools_are_offered_whatever_the_provider():
    asyncio.run(_test_tools_are_offered_whatever_the_provider())


async def _test_tools_are_offered_whatever_the_provider():
    """No capability table knows this endpoint; it is offered tools anyway."""
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "Answer."},
                    finish_reason="stop",
                )
            ]
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: FakeRedis()),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm("scaleway/mistral-small"),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    assert message.content == "Answer."
    assert [tool["function"]["name"] for tool in calls[0]["tools"]] == ["web_search"]


def test_provider_rejection_answers_and_is_remembered():
    asyncio.run(_test_provider_rejection_answers_and_is_remembered())


async def _test_provider_rejection_answers_and_is_remembered():
    """A provider refusing tools still answers, and the refusal is stored."""
    calls: list[dict[str, Any]] = []
    redis = FakeRedis()

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        if "tools" in kwargs:
            raise litellm.BadRequestError(
                message="tools is not supported",
                model="scaleway/mistral-small",
                llm_provider="scaleway",
            )
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "Fallback answer."},
                    finish_reason="stop",
                )
            ]
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: redis),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm("scaleway/mistral-small"),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

        # Asserted inside the patch: the rejection lives in Redis.
        assert tools.model_rejects_tools("scaleway/mistral-small")

    assert message.content == "Fallback answer."
    assert "tools" in calls[0]
    assert "tools" not in calls[1]


def test_remembered_rejection_skips_the_wasted_request():
    asyncio.run(_test_remembered_rejection_skips_the_wasted_request())


async def _test_remembered_rejection_skips_the_wasted_request():
    """Once a model is known to refuse tools, it is never offered them again."""
    calls: list[dict[str, Any]] = []
    redis = FakeRedis()

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "Answer."},
                    finish_reason="stop",
                )
            ]
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: redis),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        tools.remember_tool_rejection("scaleway/mistral-small")
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm("scaleway/mistral-small"),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    assert message.content == "Answer."
    assert len(calls) == 1
    assert "tools" not in calls[0]


def test_unrelated_bad_request_is_not_swallowed():
    asyncio.run(_test_unrelated_bad_request_is_not_swallowed())


async def _test_unrelated_bad_request_is_not_swallowed():
    """A 400 that has nothing to do with tools still reaches the caller."""
    redis = FakeRedis()

    async def fake_completion(**kwargs):
        raise litellm.BadRequestError(
            message="temperature must be between 0 and 2",
            model="scaleway/mistral-small",
            llm_provider="scaleway",
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: redis),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        message = LLMMessageCreate()
        raised = False
        try:
            async for _ in integration.litellm_stream_iter(
                llm=_llm("scaleway/mistral-small"),
                messages=[UserMessage(content="Hello")],
                msg=message,
                temperature=0.7,
                max_new_tokens=100,
                tools=_web_search_tools(),
            ):
                pass
        except litellm.BadRequestError:
            raised = True

    assert raised


async def _test_disabled_search_does_not_expose_tools():
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "No search."},
                    finish_reason="stop",
                )
            ]
        )

    with patch.object(integration.litellm, "acompletion", fake_completion):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=[],
        ):
            pass

    assert message.content == "No search."
    assert "tools" not in calls[0]
    assert "tool_choice" not in calls[0]


def test_enabled_model_can_choose_not_to_search():
    asyncio.run(_test_enabled_model_can_choose_not_to_search())


async def _test_enabled_model_can_choose_not_to_search():
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "Already known."},
                    finish_reason="stop",
                )
            ]
        )

    async def unexpected_search(*args, **kwargs):
        raise AssertionError("Search should not run")

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(
            integration.litellm, "supports_function_calling", return_value=True
        ),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
        patch.object(web_search, "search_web", unexpected_search),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Say hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    assert message.content == "Already known."
    assert calls[0]["tool_choice"] == "auto"


def test_missing_linkup_key_does_not_expose_tools():
    asyncio.run(_test_missing_linkup_key_does_not_expose_tools())


async def _test_missing_linkup_key_does_not_expose_tools():
    calls: list[dict[str, Any]] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "Fallback."},
                    finish_reason="stop",
                )
            ]
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(web_search.settings, "LINKUP_API_KEY", None),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    assert message.content == "Fallback."
    assert "tools" not in calls[0]


def test_invalid_tool_arguments_return_error_without_search():
    asyncio.run(_test_invalid_tool_arguments_return_error_without_search())


async def _test_invalid_tool_arguments_return_error_without_search():
    called = False

    async def fake_search(query: str, raise_on_error: bool = False):
        nonlocal called
        called = True
        return []

    with patch.object(web_search, "search_web", fake_search):
        result = await web_search.execute_web_search('{"query":""}')

    assert called is False
    assert result.results == []
    assert "Invalid arguments" in result.content


def test_fragmented_streamed_tool_arguments_are_reconstructed():
    asyncio.run(_test_fragmented_streamed_tool_arguments_are_reconstructed())


async def _test_fragmented_streamed_tool_arguments_are_reconstructed():
    calls: list[dict[str, Any]] = []
    queries: list[str] = []

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return AsyncChunkStream(
                [
                    _chunk(
                        response_id="tool",
                        delta={
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "web_search",
                                        "arguments": '{"query":"latest ',
                                    },
                                }
                            ],
                        },
                    ),
                    _chunk(
                        response_id="tool",
                        delta={
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "function": {"arguments": 'news"}'},
                                }
                            ]
                        },
                        finish_reason="tool_calls",
                    ),
                ]
            )
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="final",
                    delta={"role": "assistant", "content": "Done."},
                    finish_reason="stop",
                )
            ]
        )

    async def fake_search(query: str, raise_on_error: bool = False):
        queries.append(query)
        return []

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(
            integration.litellm, "supports_function_calling", return_value=True
        ),
        patch.object(web_search.settings, "LINKUP_API_KEY", "test"),
        patch.object(web_search, "search_web", fake_search),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Search")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    assert queries == ["latest news"]
    assert message.content == "Done."


def test_tool_call_budget_forces_a_final_answer():
    asyncio.run(_test_tool_call_budget_forces_a_final_answer())


async def _test_tool_call_budget_forces_a_final_answer():
    calls: list[dict[str, Any]] = []
    search_count = 0

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        if "tools" not in kwargs:
            return AsyncChunkStream(
                [
                    _chunk(
                        response_id="final",
                        delta={"role": "assistant", "content": "Budget reached."},
                        finish_reason="stop",
                    )
                ]
            )
        call_number = len(calls)
        return AsyncChunkStream(
            [
                _chunk(
                    response_id=f"tool-{call_number}",
                    delta={
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": f"call-{call_number}",
                                "type": "function",
                                "function": {
                                    "name": "web_search",
                                    "arguments": f'{{"query":"query {call_number}"}}',
                                },
                            }
                        ],
                    },
                    finish_reason="tool_calls",
                )
            ]
        )

    async def fake_search(query: str, raise_on_error: bool = False):
        nonlocal search_count
        search_count += 1
        return []

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: FakeRedis()),
        patch.object(web_search.settings, "LINKUP_API_KEY", "test"),
        patch.object(web_search, "search_web", fake_search),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Keep searching")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    # This model asks for one search per round, so the round guard bites before
    # the call guard. Either way it is forced to answer, and says which stopped it.
    assert search_count == integration.MAX_TOOL_ROUNDS
    assert len(calls) == integration.MAX_TOOL_ROUNDS + 1
    assert message.content == "Budget reached."
    assert message.agent_stop_reason == "round_limit"


def test_search_results_are_safe_and_bounded():
    results = [
        LinkupSearchTextResult(
            type="text",
            name=f"Result {index}",
            url=(
                "javascript:alert(1)" if index == 0 else f"https://example.com/{index}"
            ),
            content="x" * (web_search.WEB_SEARCH_MAX_RESULT_CONTENT_LENGTH + 10),
        )
        for index in range(web_search.WEB_SEARCH_MAX_RESULTS_PER_CALL + 3)
    ]

    normalized = web_search._normalize_search_results(results)

    assert len(normalized) <= web_search.WEB_SEARCH_MAX_RESULTS_PER_CALL - 1
    assert all(result.url.startswith("https://") for result in normalized)
    assert sum(len(result.content) for result in normalized) <= (
        web_search.WEB_SEARCH_MAX_TOTAL_CONTENT_LENGTH
    )
    assert all(
        len(result.content) <= web_search.WEB_SEARCH_MAX_RESULT_CONTENT_LENGTH
        for result in normalized
    )


def test_search_timeout_and_failure_become_tool_errors():
    asyncio.run(_test_search_timeout_and_failure_become_tool_errors())


async def _test_search_timeout_and_failure_become_tool_errors():
    arguments_json = '{"query":"news"}'

    async def slow_search(*args, **kwargs):
        await asyncio.sleep(0.02)
        return []

    with (
        patch.object(web_search, "search_web", slow_search),
        patch.object(web_search, "WEB_SEARCH_TOOL_TIMEOUT_SECONDS", 0.001),
    ):
        timeout_content = (await web_search.execute_web_search(arguments_json)).content

    async def failing_search(*args, **kwargs):
        raise RuntimeError("provider details must not leak")

    with patch.object(web_search, "search_web", failing_search):
        failure_content = (await web_search.execute_web_search(arguments_json)).content

    assert "timed out" in timeout_content
    assert "failed" in failure_content
    assert "provider details" not in failure_content


def test_parallel_scheduler_does_not_cancel_slower_stream():
    asyncio.run(_test_parallel_scheduler_does_not_cancel_slower_stream())


async def _test_parallel_scheduler_does_not_cancel_slower_stream():
    # Importing the streaming module initializes the database engine, but this
    # unit test never connects to it.
    integration.settings.COMPARIA_DB_URI = (
        integration.settings.COMPARIA_DB_URI
        or "postgresql://test:test@localhost:5432/test"
    )
    from backend.arena import streaming

    turn = SimpleNamespace(
        user_msg=UserMessage(content="Hello"),
        llm_msg_a=None,
        llm_msg_b=None,
    )
    comparison = SimpleNamespace(
        turns=[turn],
        llm_id_a="model-a",
        llm_id_b="model-b",
        system_msg_a=None,
        system_msg_b=None,
        mode="random",
        custom_models_selection=None,
        enabled_tools=["web_search"],
    )
    llms_data = SimpleNamespace(
        enabled={"model-a": SimpleNamespace(), "model-b": SimpleNamespace()}
    )

    async def fake_get_llms_data():
        return llms_data

    async def fake_stream(pos, *args, **kwargs):
        delays = (0, 0, 0) if pos == "a" else (0.01, 0.01)
        for index, delay in enumerate(delays):
            await asyncio.sleep(delay)
            yield {
                "type": "chunk",
                "pos": pos,
                "llm_msg": LLMMessageCreate(content=f"{pos}-{index}"),
            }
        yield {"type": "complete", "pos": pos}

    async def no_tools(_keys):
        return []

    with (
        patch.object(streaming, "get_llms_data", fake_get_llms_data),
        patch.object(streaming, "stream_llm_response", fake_stream),
        patch.object(streaming, "resolve_tools", no_tools),
    ):
        events = [
            event
            async for event in streaming.stream_comparison_messages(comparison, turn)
        ]

    b_chunks = [
        event for event in events if event["type"] == "chunk" and event["pos"] == "b"
    ]
    assert len(b_chunks) == 2
    assert events[-1] == {"type": "complete"}


def test_response_cache_is_bypassed_when_tools_are_available():
    asyncio.run(_test_response_cache_is_bypassed_when_tools_are_available())


async def _test_response_cache_is_bypassed_when_tools_are_available():
    integration.settings.COMPARIA_DB_URI = (
        integration.settings.COMPARIA_DB_URI
        or "postgresql://test:test@localhost:5432/test"
    )
    from backend.arena import conversation

    async def fake_stream_iter(*, msg, **kwargs):
        now = datetime.now()
        msg.created_at = now
        msg.responded_at = now
        msg.updated_at = now
        msg.content = "Fresh answer."
        msg.tokens = 2
        msg.generation_id = "fresh"
        yield msg

    def unexpected_cache_call(*args, **kwargs):
        raise AssertionError("Response cache must be bypassed when tools are enabled")

    turn = SimpleNamespace(
        user_msg=UserMessage(content="Current events?"),
        llm_msg_a=None,
        llm_msg_b=None,
    )
    llm = SimpleNamespace(
        id="model-a",
        human_id="model-a",
        endpoint=SimpleNamespace(api_model_id="model-a"),
    )

    with (
        patch.object(conversation, "get_cached_response", unexpected_cache_call),
        patch.object(conversation, "store_cached_response", unexpected_cache_call),
        patch.object(conversation, "litellm_stream_iter", fake_stream_iter),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        messages = [
            message.content
            async for message in conversation.bot_response_async(
                pos="a",
                llm=llm,
                turn=turn,
                turn_index=0,
                messages=[turn.user_msg],
                tools=_web_search_tools(),
            )
        ]

    assert messages[-1] == "Fresh answer."


def test_web_search_sources_reach_their_own_column():
    asyncio.run(_test_web_search_sources_reach_their_own_column())


async def _test_web_search_sources_reach_their_own_column():
    integration.settings.COMPARIA_DB_URI = (
        integration.settings.COMPARIA_DB_URI
        or "postgresql://test:test@localhost:5432/test"
    )
    from backend.arena import conversation

    result = LinkupSearchTextResult(
        type="text",
        name="Example",
        url="https://example.com/news",
        content="Fresh information",
    )

    async def fake_stream_iter(*, msg, **kwargs):
        now = datetime.now()
        msg.created_at = now
        msg.responded_at = now
        msg.updated_at = now
        msg.generation_id = "sourced"
        msg.tokens = 2
        msg.agent_trace = [
            AgentTraceToolResult(
                tool_call_id="call-1",
                name=web_search.WEB_SEARCH_TOOL_NAME,
                status="success",
                duration_ms=12,
                content='{"results":[]}',
                results=[result],
            )
        ]
        yield msg
        msg.content = "Sourced answer."
        yield msg

    turn = SimpleNamespace(
        user_msg=UserMessage(content="Current events?"),
        llm_msg_a=None,
        llm_msg_b=None,
    )
    llm = SimpleNamespace(
        id="model-a",
        human_id="model-a",
        endpoint=SimpleNamespace(api_model_id="model-a"),
    )

    with patch.object(conversation, "litellm_stream_iter", fake_stream_iter):
        streamed = [
            message.web_search_results
            async for message in conversation.bot_response_async(
                pos="a",
                llm=llm,
                turn=turn,
                turn_index=0,
                messages=[turn.user_msg],
                tools=_web_search_tools(),
            )
        ]

    # The results accordion reads this column while the answer is still coming.
    assert streamed[0] == [result]
    assert streamed[-1] == [result]


def test_search_results_are_json_native_at_persistence_boundary():
    integration.settings.COMPARIA_DB_URI = (
        integration.settings.COMPARIA_DB_URI
        or "postgresql://test:test@localhost:5432/test"
    )
    from backend.arena.services import _llm_message_for_persistence

    result = LinkupSearchTextResult(
        type="text",
        name="Example",
        url="https://example.com/news",
        content="Fresh information",
    )
    now = datetime.now()
    db_message = _llm_message_for_persistence(
        LLMMessageCreate(
            content="Sourced answer.",
            created_at=now,
            responded_at=now,
            updated_at=now,
            generation_id="test-generation",
            tokens=10,
            web_search_results=[result],
            agent_trace=[
                AgentTraceToolCall(
                    tool_call_id="call-1",
                    name="web_search",
                    arguments_json='{"query":"current news"}',
                    arguments={"query": "current news"},
                ),
                AgentTraceToolResult(
                    tool_call_id="call-1",
                    name="web_search",
                    status="success",
                    duration_ms=25,
                    content='{"results":[]}',
                    results=[result],
                ),
            ],
        )
    )

    assert db_message.web_search_results == [result.model_dump(mode="json")]
    assert [event["type"] for event in db_message.agent_trace] == [
        "tool_call",
        "tool_result",
    ]
    json.dumps(db_message.web_search_results)
    json.dumps(db_message.agent_trace)


def _tool_call_delta(*calls: tuple[str, str, str]) -> dict[str, Any]:
    """Build the streamed delta for one or more tool calls."""
    return {
        "tool_calls": [
            {
                "index": index,
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments},
            }
            for index, (call_id, name, arguments) in enumerate(calls)
        ]
    }


def _spy_tool(name: str, run) -> tools.ToolSpec:
    return tools.ToolSpec(
        name=name,
        schema={
            "type": "function",
            "function": {
                "name": name,
                "description": "test tool",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        run=run,
    )


def test_calls_in_one_round_run_concurrently():
    asyncio.run(_test_calls_in_one_round_run_concurrently())


async def _test_calls_in_one_round_run_concurrently():
    """Three calls emitted together overlap instead of queueing."""
    in_flight = 0
    peak = 0

    async def slow(_arguments: str) -> tools.ToolResult:
        nonlocal in_flight, peak
        in_flight += 1
        peak = max(peak, in_flight)
        await asyncio.sleep(0.05)
        in_flight -= 1
        return tools.ToolResult(content="{}", status="success")

    responses = [
        AsyncChunkStream(
            [
                _chunk(
                    response_id="round-1",
                    delta={"role": "assistant"},
                ),
                _chunk(
                    response_id="round-1",
                    delta=_tool_call_delta(
                        ("call-1", "slow", "{}"),
                        ("call-2", "slow", "{}"),
                        ("call-3", "slow", "{}"),
                    ),
                    finish_reason="tool_calls",
                ),
            ]
        ),
        AsyncChunkStream(
            [
                _chunk(
                    response_id="final",
                    delta={"role": "assistant", "content": "Done."},
                    finish_reason="stop",
                )
            ]
        ),
    ]

    async def fake_completion(**_kwargs):
        return responses.pop(0)

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: FakeRedis()),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=[_spy_tool("slow", slow)],
        ):
            pass

    assert peak == 3, f"expected three overlapping calls, saw {peak}"
    assert message.content == "Done."


def test_time_budget_stops_tool_use_and_is_recorded():
    asyncio.run(_test_time_budget_stops_tool_use_and_is_recorded())


async def _test_time_budget_stops_tool_use_and_is_recorded():
    """Past the deadline the model is offered no tools and must answer."""
    calls: list[dict[str, Any]] = []

    async def slow(_arguments: str) -> tools.ToolResult:
        await asyncio.sleep(0.05)
        return tools.ToolResult(content="{}", status="success")

    def tool_round(response_id: str, call_id: str):
        return AsyncChunkStream(
            [
                _chunk(response_id=response_id, delta={"role": "assistant"}),
                _chunk(
                    response_id=response_id,
                    delta=_tool_call_delta((call_id, "slow", "{}")),
                    finish_reason="tool_calls",
                ),
            ]
        )

    responses = [
        tool_round("round-1", "call-1"),
        AsyncChunkStream(
            [
                _chunk(
                    response_id="final",
                    delta={"role": "assistant", "content": "Answer without more."},
                    finish_reason="stop",
                )
            ]
        ),
    ]

    async def fake_completion(**kwargs):
        calls.append(kwargs)
        return responses.pop(0)

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: FakeRedis()),
        patch.object(integration, "TOOL_TIME_BUDGET_SECONDS", 0.01),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=[_spy_tool("slow", slow)],
        ):
            pass

    assert message.content == "Answer without more."
    assert "tools" in calls[0]
    assert "tools" not in calls[1]
    assert message.agent_stop_reason == "deadline"


def test_finishing_normally_records_completion():
    asyncio.run(_test_finishing_normally_records_completion())


async def _test_finishing_normally_records_completion():
    """A model that stops on its own is not recorded as cut off."""

    async def fake_completion(**_kwargs):
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="plain",
                    delta={"role": "assistant", "content": "No tool needed."},
                    finish_reason="stop",
                )
            ]
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: FakeRedis()),
        patch.object(web_search.settings, "LINKUP_API_KEY", "configured-for-test"),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=_web_search_tools(),
        ):
            pass

    assert message.agent_stop_reason == "completed"


def test_context_overflow_sheds_tool_rounds_and_still_answers():
    asyncio.run(_test_context_overflow_sheds_tool_rounds_and_still_answers())


async def _test_context_overflow_sheds_tool_rounds_and_still_answers():
    """A conversation that outgrows its window answers instead of failing."""
    sent: list[list[dict[str, Any]]] = []

    async def quick(_arguments: str) -> tools.ToolResult:
        return tools.ToolResult(content='{"results": []}', status="success")

    state = {"round": 0}

    async def fake_completion(**kwargs):
        sent.append(kwargs["messages"])
        state["round"] += 1
        if state["round"] == 1:
            return AsyncChunkStream(
                [
                    _chunk(response_id="round-1", delta={"role": "assistant"}),
                    _chunk(
                        response_id="round-1",
                        delta=_tool_call_delta(("call-1", "quick", "{}")),
                        finish_reason="tool_calls",
                    ),
                ]
            )
        if state["round"] == 2:
            raise litellm.ContextWindowExceededError(
                message="too long",
                model="test-model",
                llm_provider="test",
            )
        return AsyncChunkStream(
            [
                _chunk(
                    response_id="final",
                    delta={"role": "assistant", "content": "Shorter answer."},
                    finish_reason="stop",
                )
            ]
        )

    with (
        patch.object(integration.litellm, "acompletion", fake_completion),
        patch.object(tools, "get_redis_client", lambda: FakeRedis()),
    ):
        message = LLMMessageCreate()
        async for _ in integration.litellm_stream_iter(
            llm=_llm(),
            messages=[UserMessage(content="Hello")],
            msg=message,
            temperature=0.7,
            max_new_tokens=100,
            tools=[_spy_tool("quick", quick)],
        ):
            pass

    assert message.content == "Shorter answer."
    # The retry carries no tool traffic: the whole round was shed.
    assert not [m for m in sent[-1] if m.get("role") == "tool"]


if __name__ == "__main__":
    tests = [
        test_model_can_search_then_stream_final_answer,
        test_disabled_search_does_not_expose_tools,
        test_tools_are_offered_whatever_the_provider,
        test_provider_rejection_answers_and_is_remembered,
        test_remembered_rejection_skips_the_wasted_request,
        test_unrelated_bad_request_is_not_swallowed,
        test_enabled_model_can_choose_not_to_search,
        test_missing_linkup_key_does_not_expose_tools,
        test_invalid_tool_arguments_return_error_without_search,
        test_fragmented_streamed_tool_arguments_are_reconstructed,
        test_tool_call_budget_forces_a_final_answer,
        test_search_results_are_safe_and_bounded,
        test_search_timeout_and_failure_become_tool_errors,
        test_parallel_scheduler_does_not_cancel_slower_stream,
        test_response_cache_is_bypassed_when_tools_are_available,
        test_web_search_sources_reach_their_own_column,
        test_search_results_are_json_native_at_persistence_boundary,
        test_calls_in_one_round_run_concurrently,
        test_time_budget_stops_tool_use_and_is_recorded,
        test_finishing_normally_records_completion,
        test_context_overflow_sheds_tool_rounds_and_still_answers,
    ]
    for test in tests:
        test()
    print(f"{len(tests)} agentic web search tests passed.")
