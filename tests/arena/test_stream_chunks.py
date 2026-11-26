"""What each streamed chunk sends to the browser while a model uses tools."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import patch

from backend.arena import litellm as integration
from utils.database.models import (
    AgentTraceToolCall,
    AgentTraceToolResult,
    LLMMessageCreate,
    ToolSource,
)


def _streaming():
    # Importing the module sets up the database engine; these tests never
    # connect to it.
    integration.settings.COMPARIA_DB_URI = (
        integration.settings.COMPARIA_DB_URI
        or "postgresql://test:test@localhost:5432/test"
    )
    from backend.arena import streaming

    return streaming


def _call() -> AgentTraceToolCall:
    return AgentTraceToolCall(tool_call_id="1", name="search", arguments_json="{}")


def _result(content: str, sources: list[ToolSource]) -> AgentTraceToolResult:
    return AgentTraceToolResult(
        tool_call_id="1",
        name="search",
        status="success",
        duration_ms=10,
        content=content,
        results=sources,
    )


def test_steps_go_out_once_however_long_the_answer():
    asyncio.run(_test_steps_go_out_once_however_long_the_answer())


async def _test_steps_go_out_once_however_long_the_answer():
    streaming = _streaming()

    big = "x" * 10_000
    sourced = _result(big, [ToolSource(name="Page", url="https://a.fr", content=big)])

    async def fake_bot_response(*args, **kwargs):
        msg = LLMMessageCreate(content="")
        msg.agent_trace = [_call()]
        yield msg
        msg.agent_trace.append(sourced)
        yield msg
        for word in range(200):
            msg.content += f" mot{word}"
            yield msg

    with patch.object(streaming, "bot_response_async", fake_bot_response):
        events = [
            event
            async for event in streaming.stream_llm_response(
                "a", SimpleNamespace(id="m"), None, 0, []
            )
        ]

    chunks = [event["llm_msg"] for event in events if event["type"] == "chunk"]
    with_steps = [chunk for chunk in chunks if "agent_trace" in chunk]
    assert len(chunks) == 202
    assert [len(chunk["agent_trace"]) for chunk in with_steps] == [1, 2]
    assert all("web_search_results" not in chunk for chunk in chunks)
    # The arena shows the sources; the raw text they were parsed from stays home.
    assert with_steps[-1]["agent_trace"][1]["content"] == ""
    assert with_steps[-1]["agent_trace"][1]["results"][0]["content"] == big
    total = sum(len(streaming.format_sse_event(event)) for event in events)
    assert total < 3 * len(big) + 200 * 2_000
    assert chunks[-1]["content"].endswith("mot199")


def test_a_result_without_sources_keeps_its_text():
    streaming = _streaming()

    msg = LLMMessageCreate(content="")
    msg.agent_trace = [_call(), _result(json.dumps({"answer": "42"}), [])]

    sent = streaming.chunk_message(msg, send_trace=True)

    assert sent["agent_trace"][1]["content"] == '{"answer": "42"}'
