"""
A slow model must only slow its own comparison.

The backend serves every visitor from one event loop. A provider read that
blocks it stalls every other request until the provider answers, and the
health check with them. These tests stream from a model that takes its time
and check that the loop keeps turning, that the two answers of a comparison
do not wait on each other, and that a visitor who leaves closes both
provider streams.

Nothing leaves the machine: the slow provider is a local HTTP server or an
in-memory fake.

Run with pytest:
    uv run pytest tests/arena/test_stream_event_loop.py
"""

import asyncio
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, AsyncGenerator, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import litellm  # noqa: E402
import pytest  # noqa: E402
from litellm.types.utils import (  # noqa: E402
    Delta,
    ModelResponseStream,
    StreamingChoices,
)

import backend.arena.litellm as arena_litellm  # noqa: E402
import backend.arena.streaming as streaming  # noqa: E402
from backend.arena.conversation import bot_response_async  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.llms.models import LitellmEndpoint  # noqa: E402
from utils.database.models import LLMMessageCreate, UserMessageRead  # noqa: E402

# Long enough that a blocked loop is obvious, short enough to keep the suite fast.
PROVIDER_PAUSE = 0.6
# What the loop may stall for when nothing blocks it, with room for a busy CI.
TOLERATED_STALL = 0.25


def chunk(delta: dict, finish_reason: str | None = None) -> dict:
    return {
        "id": "gen-slow",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "slow",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


SLOW_STREAM = [
    chunk({"role": "assistant", "reasoning_content": "Je réfléchis. "}),
    chunk({"content": "Bonjour"}),
    chunk({"content": " à vous."}),
    chunk({}, finish_reason="stop"),
    {
        "id": "gen-slow",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "slow",
        "choices": [],
        "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7},
    },
]


class SlowProvider(BaseHTTPRequestHandler):
    """OpenAI-compatible endpoint that pauses before every chunk."""

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for event in SLOW_STREAM:
            time.sleep(PROVIDER_PAUSE)
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, *_args):
        pass


@pytest.fixture
def slow_provider():
    server = ThreadingHTTPServer(("127.0.0.1", 0), SlowProvider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/v1"
    finally:
        server.shutdown()
        server.server_close()


def llm_at(base_url: str):
    return SimpleNamespace(
        id="slow-llm",
        human_id="slow-llm",
        endpoint=SimpleNamespace(api_model_id="slow"),
        litellm_endpoint=LitellmEndpoint(
            model="openai/slow", base_url=base_url, api_key="dummy", api_version=None
        ),
    )


async def longest_stall_while(work, measuring: asyncio.Event) -> tuple[float, Any]:
    """
    Run `work` and report the longest the loop went without turning once
    `measuring` is set.
    """
    longest = 0.0
    stop = asyncio.Event()

    async def heartbeat():
        nonlocal longest
        last = time.monotonic()
        while not stop.is_set():
            await asyncio.sleep(0.01)
            now = time.monotonic()
            if measuring.is_set():
                longest = max(longest, now - last)
            last = now

    beat = asyncio.create_task(heartbeat())
    await asyncio.sleep(0.05)
    try:
        result = await work
    finally:
        stop.set()
        await beat
    return longest, result


def test_the_loop_keeps_serving_while_a_provider_is_slow(slow_provider, monkeypatch):
    monkeypatch.setattr(settings, "MOCK_RESPONSE", False)
    # The first call of a process imports the provider client, several
    # hundred modules, on the loop. That is a one-off cost, not a slow model.
    import openai.resources  # noqa: F401

    turn: Any = SimpleNamespace()
    user_msg = UserMessageRead(content="Bonjour ?")

    async def answer(first_chunk: asyncio.Event) -> list[LLMMessageCreate]:
        updates = []
        async for msg in bot_response_async(
            "a", llm_at(slow_provider), turn, 1, [user_msg]
        ):
            first_chunk.set()
            updates.append(msg.model_copy())
        return updates

    async def scenario():
        # Measured from the first chunk on: the setup before it is litellm's,
        # and every later chunk still waits a full pause on the provider.
        first_chunk = asyncio.Event()
        return await longest_stall_while(answer(first_chunk), first_chunk)

    started = time.monotonic()
    stall, updates = asyncio.run(scenario())
    took = time.monotonic() - started

    # The answer really was slow, and the loop kept turning all the same.
    assert took >= 3 * PROVIDER_PAUSE
    assert stall < TOLERATED_STALL, f"event loop stalled for {stall:.2f}s"

    final = updates[-1]
    assert final.content == "Bonjour à vous."
    assert final.reasoning_content == "Je réfléchis. "
    assert final.generation_id == "gen-slow"
    # The stream stops reading at "stop", before the usage chunk, so the
    # count comes from the local fallback, as it did with the sync read.
    assert final.tokens
    assert final.created_at <= final.responded_at <= final.updated_at
    assert turn.llm_msg_a == final


def test_the_mock_response_still_streams(monkeypatch):
    monkeypatch.setattr(settings, "MOCK_RESPONSE", True)
    turn: Any = SimpleNamespace()
    user_msg = UserMessageRead(content="Bonjour ?")

    async def answer() -> list[LLMMessageCreate]:
        return [
            msg.model_copy()
            async for msg in bot_response_async(
                "b", llm_at("http://127.0.0.1:9/v1"), turn, 1, [user_msg]
            )
        ]

    updates = asyncio.run(answer())
    assert len(updates) > 1
    assert (
        updates[-1].content
        == "This is a fake response that didn't contact the LLM api."
    )
    assert updates[-1].tokens


class EndlessStream:
    """Provider stream that sends one chunk, then keeps the visitor waiting."""

    def __init__(self):
        self.sent = False
        self.closed = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.sent:
            self.sent = True
            return ModelResponseStream(
                id="gen-endless",
                choices=[StreamingChoices(delta=Delta(content="Un début"))],
            )
        await asyncio.sleep(3600)

    async def aclose(self):
        self.closed = True


def test_leaving_mid_answer_closes_the_provider_stream(monkeypatch):
    monkeypatch.setattr(settings, "MOCK_RESPONSE", False)
    stream = EndlessStream()

    async def acompletion(**_kwargs):
        return stream

    def completion(**_kwargs):
        raise AssertionError("the provider must not be read on the event loop")

    monkeypatch.setattr(arena_litellm.litellm, "acompletion", acompletion)
    monkeypatch.setattr(arena_litellm.litellm, "completion", completion)

    async def scenario():
        first = asyncio.Event()

        async def visitor():
            async for _msg in bot_response_async(
                "a",
                llm_at("http://127.0.0.1:9/v1"),
                cast(Any, SimpleNamespace()),
                1,
                [UserMessageRead(content="Bonjour ?")],
            ):
                first.set()

        task = asyncio.create_task(visitor())
        await asyncio.wait_for(first.wait(), timeout=2)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        # Checked before the loop shuts down, which would close it anyway.
        return stream.closed

    assert asyncio.run(scenario())


# Two models answering one comparison: one quick, one that dawdles.


def comparison_between(fast: str, slow: str):
    return SimpleNamespace(
        id="comparison",
        turns=[SimpleNamespace(llm_msg_a=None, llm_msg_b=None, user_msg=None)],
        llm_id_a=fast,
        llm_id_b=slow,
        system_msg_a=None,
        system_msg_b=None,
        mode="random",
        custom_models_selection=None,
        error=None,
    )


def fake_models(
    monkeypatch,
    pauses: dict[str, float],
    closed: set[str],
    times_out: str | None = None,
) -> list:
    """
    Each model answers three words, pausing before each one, except
    `times_out`, which gives up after its first. Returns the errors the
    comparison would have saved.
    """

    async def bot_response_async(
        pos, llm, turn, turn_index, messages, request=None
    ) -> AsyncGenerator[LLMMessageCreate]:
        msg = LLMMessageCreate()
        try:
            for word in ("un", "deux", "trois"):
                await asyncio.sleep(pauses[llm.id])
                msg.content += word
                yield msg
                if llm.id == times_out:
                    raise litellm.Timeout(
                        message="too slow", model=llm.id, llm_provider="openai"
                    )
        finally:
            closed.add(llm.id)

    async def get_llms_data():
        return SimpleNamespace(
            enabled={
                llm_id: SimpleNamespace(
                    id=llm_id, endpoint=SimpleNamespace(api_type="openai")
                )
                for llm_id in pauses
            }
        )

    errors: list = []

    async def update_comparison_error(_comparison, error):
        errors.append(error)

    monkeypatch.setattr(streaming, "bot_response_async", bot_response_async)
    monkeypatch.setattr(streaming, "get_llms_data", get_llms_data)
    monkeypatch.setattr(streaming, "update_comparison_error", update_comparison_error)
    return errors


def test_a_slow_model_does_not_hold_back_or_cut_the_other(monkeypatch):
    closed: set[str] = set()
    errors = fake_models(monkeypatch, {"fast": 0.01, "slow": 0.2}, closed)
    comparison = comparison_between("fast", "slow")

    async def collect():
        return [
            event
            async for event in streaming.stream_comparison_messages(
                comparison, comparison.turns[0]
            )
        ]

    events = asyncio.run(collect())
    order = [(e["type"], e.get("pos")) for e in events]

    # The quick answer is done before the slow one has written its second word.
    assert (
        order.index(("complete", "a"))
        < [i for i, e in enumerate(order) if e == ("chunk", "b")][1]
    )
    # And the slow one arrives whole: no word lost to a cancelled read.
    slow_chunks = [e for e in events if e["type"] == "chunk" and e["pos"] == "b"]
    assert len(slow_chunks) == 3
    assert slow_chunks[-1]["llm_msg"].content == "undeuxtrois"
    assert order[-1] == ("complete", None)
    assert all(e["type"] != "error" for e in events)
    assert not errors


def test_a_visitor_who_leaves_closes_both_provider_streams(monkeypatch):
    closed: set[str] = set()
    errors = fake_models(monkeypatch, {"fast": 0.01, "slow": 3600}, closed)
    comparison = comparison_between("fast", "slow")

    async def scenario():
        fast_done = asyncio.Event()

        async def visitor():
            async for event in streaming.stream_comparison_messages(
                comparison, comparison.turns[0]
            ):
                if event == {"type": "complete", "pos": "a"}:
                    fast_done.set()

        task = asyncio.create_task(visitor())
        await asyncio.wait_for(fast_done.wait(), timeout=2)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        # Give anything left running a turn to show itself.
        await asyncio.sleep(0.05)
        # Checked before the loop shuts down, which would close them anyway.
        leftover = {t for t in asyncio.all_tasks() if t is not asyncio.current_task()}
        return set(closed), leftover

    closed_in_time, leftover = asyncio.run(scenario())
    assert closed_in_time == {"fast", "slow"}
    assert not leftover
    assert not errors


def test_a_model_that_times_out_is_swapped_while_the_other_streams(monkeypatch):
    closed: set[str] = set()
    errors = fake_models(
        monkeypatch,
        {"steady": 0.05, "stuck": 0.01, "spare": 0.01},
        closed,
        times_out="stuck",
    )

    async def pick_replacement_model(_comparison, _pos):
        return "spare"

    async def update_comparison_llm_id(comparison, pos, llm_id):
        setattr(comparison, f"llm_id_{pos}", llm_id)

    monkeypatch.setattr(streaming, "pick_replacement_model", pick_replacement_model)
    monkeypatch.setattr(streaming, "update_comparison_llm_id", update_comparison_llm_id)
    comparison = comparison_between("steady", "stuck")

    async def collect():
        return [
            event
            async for event in streaming.stream_comparison_messages(
                comparison, comparison.turns[0]
            )
        ]

    events = asyncio.run(collect())
    answers = {
        pos: [
            e["llm_msg"].content
            for e in events
            if e["type"] == "chunk" and e["pos"] == pos
        ]
        for pos in ("a", "b")
    }

    assert {"type": "swap", "pos": "b"} in events
    assert comparison.llm_id_b == "spare"
    assert answers["a"][-1] == "undeuxtrois"
    assert answers["b"][-1] == "undeuxtrois"
    assert events[-1] == {"type": "complete"}
    assert not errors
    assert closed == {"steady", "stuck", "spare"}
