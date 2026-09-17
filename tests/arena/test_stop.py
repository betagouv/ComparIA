"""
Unit tests for stopping a generation (no DB, no Redis, no provider).

Run with pytest, or directly:
    uv run python tests/arena/test_stop.py
"""

import asyncio
import contextlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402

import backend.arena.conversation as conversation  # noqa: E402
import backend.arena.router as router  # noqa: E402
import backend.arena.session as session  # noqa: E402
import backend.arena.streaming as streaming  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from utils.database.models import (  # noqa: E402
    LLMMessage,
    LLMMessageCreate,
    UserMessageRead,
)


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def setex(self, key, ttl, value):
        self.store[key] = value
        self.ttls[key] = ttl

    def get(self, key):
        return self.store.get(key)


# Stop flag in Redis


def test_a_stop_is_recorded_while_streaming_and_kept_with_the_same_ttl():
    redis = FakeRedis()
    comparison_id = uuid4()
    with patched(session, get_redis_client=lambda: redis):
        session.store_comparison_metadata(comparison_id, is_streaming=True)
        assert session.is_stop_requested(comparison_id) is False

        assert session.request_comparison_stop(comparison_id) is True
        assert session.is_stop_requested(comparison_id) is True
        assert session.retreive_comparison_metadata(comparison_id).is_streaming
        assert set(redis.ttls.values()) == {session.COMPARISON_METADATA_TTL}


def test_a_stop_after_the_answers_landed_changes_nothing():
    redis = FakeRedis()
    comparison_id = uuid4()
    with patched(session, get_redis_client=lambda: redis):
        session.store_comparison_metadata(comparison_id, is_streaming=False)
        assert session.request_comparison_stop(comparison_id) is False
        assert session.is_stop_requested(comparison_id) is False

        # Unknown comparison: same answer, no exception.
        assert session.request_comparison_stop(uuid4()) is False
        assert session.is_stop_requested(uuid4()) is False


def test_starting_the_next_turn_clears_a_stale_stop():
    redis = FakeRedis()
    comparison_id = uuid4()
    with patched(session, get_redis_client=lambda: redis):
        session.store_comparison_metadata(comparison_id, is_streaming=True)
        session.request_comparison_stop(comparison_id)
        session.store_comparison_metadata(comparison_id, is_streaming=False)
        session.store_comparison_metadata(comparison_id, is_streaming=True)
        assert session.is_stop_requested(comparison_id) is False


# Stopping the merged stream


LLM_A, LLM_B = uuid4(), uuid4()


def comparison():
    # Enough of a TurnRead for TurnPublic.model_validate to accept it.
    turn = SimpleNamespace(
        id=uuid4(),
        user_msg=UserMessageRead(content="Bonjour"),
        choice=None,
        llm_msg_a=None,
        llm_msg_b=None,
        keyword_annotations_a=[],
        keyword_annotations_b=[],
        custom_annotation_a=None,
        custom_annotation_b=None,
    )
    return (
        SimpleNamespace(
            id=uuid4(),
            llm_id_a=LLM_A,
            llm_id_b=LLM_B,
            system_msg_a=None,
            system_msg_b=None,
            mode="random",
            custom_models_selection=None,
            turns=[turn],
            error=None,
        ),
        turn,
    )


async def fake_llms_data():
    return SimpleNamespace(enabled={LLM_A: "llm-a", LLM_B: "llm-b"})


def side(words, delay, closed):
    """A model that says one of `words` every `delay` seconds, writing the
    partial answer on the turn the way bot_response_async does."""

    async def stream(pos, llm, turn, turn_index, messages, request=None):
        llm_msg = LLMMessageCreate()
        setattr(turn, f"llm_msg_{pos}", llm_msg)
        try:
            for word in words:
                await asyncio.sleep(delay)
                llm_msg.content += word
                yield {"type": "chunk", "pos": pos, "llm_msg": llm_msg}
            yield {"type": "complete", "pos": pos}
        finally:
            closed.append(pos)

    return stream


def run_stream(sides, stop_after):
    """Stream both sides, with the stop flag raised `stop_after` seconds in."""
    closed: list = []
    started = 0.0

    def stop_requested():
        return asyncio.get_running_loop().time() - started >= stop_after

    async def stream_llm_response(pos, *args, **kwargs):
        async for event in sides[pos](*((pos,) + args), **kwargs):
            yield event

    async def run():
        nonlocal started
        started = asyncio.get_running_loop().time()
        comp, turn = comparison()
        with patched(
            streaming,
            stream_llm_response=stream_llm_response,
            get_llms_data=fake_llms_data,
            STOP_POLL_INTERVAL=0.02,
        ):
            events = [
                event
                async for event in streaming.stream_comparison_messages(
                    comp, turn, stop_requested=stop_requested
                )
            ]
        return events, turn, closed

    return asyncio.run(run())


def test_a_stop_closes_both_streams_and_keeps_the_partial_answers():
    closed: list = []
    events, turn, _ = run_stream(
        {"a": side(["a1 "] * 20, 0.03, closed), "b": side(["b1 "], 0.5, closed)},
        stop_after=0.1,
    )

    assert events[-1]["type"] == "interrupted"
    assert [e["type"] for e in events[:-1]] == ["chunk"] * (len(events) - 1)
    assert 2 <= len(events) - 1 <= 5, "the stop should land within a few chunks"
    assert sorted(closed) == ["a", "b"], "a provider stream was left open"

    # Side a said something and was cut; side b had not said a word yet.
    assert turn.llm_msg_a.interrupted is True
    assert turn.llm_msg_a.content.startswith("a1 ")
    assert turn.llm_msg_b.interrupted is True
    assert turn.llm_msg_b.content == ""


def test_a_side_that_finished_before_the_stop_is_not_flagged():
    closed: list = []
    events, turn, _ = run_stream(
        {"a": side(["a1 "], 0.01, closed), "b": side(["b1 ", "b2 "], 0.2, closed)},
        stop_after=0.1,
    )

    assert events[-1]["type"] == "interrupted"
    assert ("complete", "a") in [(e["type"], e.get("pos")) for e in events]
    assert turn.llm_msg_a.interrupted is False
    assert turn.llm_msg_b.interrupted is True


def test_without_a_stop_the_stream_ends_as_before():
    closed: list = []
    events, turn, _ = run_stream(
        {"a": side(["a1 "], 0.01, closed), "b": side(["b1 "], 0.02, closed)},
        stop_after=10,
    )

    assert [(e["type"], e.get("pos")) for e in events] == [
        ("chunk", "a"),
        ("complete", "a"),
        ("chunk", "b"),
        ("complete", "b"),
        ("complete", None),
    ]
    assert not turn.llm_msg_a.interrupted and not turn.llm_msg_b.interrupted


# Making the partial answer storable


def test_a_cut_answer_with_text_is_completed_and_flagged():
    llm = cast(Any, SimpleNamespace(human_id="gpt-4o"))
    llm_msg = LLMMessageCreate(content="Il était une fois ", reasoning_content="")

    final = conversation.finalize_interrupted(llm_msg, llm)

    assert final is llm_msg
    assert final.interrupted is True
    assert final.generation_id == "interrupted"
    assert final.tokens and final.tokens > 0
    assert final.created_at and final.responded_at and final.updated_at
    # The row LLMMessage refuses is the one that would have lost the turn.
    stored = LLMMessage.model_validate(final)
    assert stored.content == "Il était une fois"
    assert stored.interrupted is True


def test_a_cut_answer_without_text_is_dropped():
    llm = cast(Any, SimpleNamespace(human_id="gpt-4o"))
    assert conversation.finalize_interrupted(LLMMessageCreate(), llm) is None
    assert (
        conversation.finalize_interrupted(
            LLMMessageCreate(content="  ", reasoning_content="hmm"), llm
        )
        is None
    )


# The route tail: what gets saved and what the browser receives


def test_the_route_saves_the_cut_answers_and_sends_them_back():
    saved: dict = {}
    released: list = []
    charged: list = []
    comp, turn = comparison()
    turn.llm_msg_a = LLMMessageCreate(content="Il était une fois ", interrupted=True)
    turn.llm_msg_b = LLMMessageCreate(interrupted=True)  # stopped before a word

    async def stream_comparison_messages(comparison, turn, request, stop_requested):
        assert stop_requested() is False  # reads the flag, not a constant
        yield {"type": "chunk", "pos": "a", "llm_msg": turn.llm_msg_a}
        yield {"type": "interrupted", "turn": None}
        raise AssertionError("the route must stop reading after the event")

    async def update_turn(id, llm_msg_a, llm_msg_b):
        saved.update(id=id, a=llm_msg_a, b=llm_msg_b)

    async def llms_data():
        llm = cast(Any, SimpleNamespace(human_id="gpt-4o"))
        return SimpleNamespace(enabled={LLM_A: llm, LLM_B: llm}, pricey_models=[])

    async def run():
        with patched(
            router,
            stream_comparison_messages=stream_comparison_messages,
            update_turn=update_turn,
            get_llms_data=llms_data,
            is_stop_requested=lambda _id: False,
            store_comparison_metadata=lambda id, is_streaming: released.append(
                is_streaming
            ),
            increment_input_chars=lambda *a, **k: charged.append(a[2]),
            get_ip=lambda request: "10.0.0.1",
        ):
            return [
                json.loads(line.removeprefix("data: "))
                async for line in router._stream_turn(
                    comp, turn, "hash", cast(Any, None)
                )
            ]

    events = asyncio.run(run())

    assert [e["type"] for e in events] == ["chunk", "interrupted"]
    assert saved["a"].interrupted is True and saved["a"].content.strip()
    assert saved["b"] is None
    assert released == [False]
    # The prompt reached both providers, so the stop costs a full turn.
    assert charged == [len(turn.user_msg.content)]
    sent = events[-1]["turn"]
    assert sent["llm_msg_a"]["interrupted"] is True
    assert sent["llm_msg_a"]["content"] == "Il était une fois "
    assert sent["llm_msg_b"] is None


# The route


def call_stop(comparison_id, read_comparison, requested: list):
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": f"/arena/stop/{comparison_id}",
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": ("10.0.0.1", 1234),
        }
    )

    def request_comparison_stop(id):
        requested.append(id)
        return True

    with patched(
        router,
        read_comparison=read_comparison,
        request_comparison_stop=request_comparison_stop,
    ):
        return asyncio.run(router.stop(comparison_id, None, "b" * 64, request))


def test_the_owner_can_stop_and_gets_204_even_when_nothing_streams():
    comparison_id = uuid4()
    requested: list = []

    async def read_comparison(id, user_id, anonymous_user_hash):
        assert (id, user_id, anonymous_user_hash) == (comparison_id, None, "b" * 64)
        return SimpleNamespace(id=id)

    assert call_stop(comparison_id, read_comparison, requested) is None
    assert requested == [comparison_id]


def test_someone_else_cannot_stop_a_comparison():
    requested: list = []

    async def read_comparison(id, user_id, anonymous_user_hash):
        raise HTTPException(status_code=404, detail="Comparison not found")

    try:
        call_stop(uuid4(), read_comparison, requested)
    except HTTPException as error:
        assert error.status_code == 404
    else:
        raise AssertionError("a stranger stopped the comparison")
    assert requested == []


def test_a_retry_drops_the_stopped_answers_from_the_transcript():
    comp, turn = comparison()
    turn.llm_msg_a = LLMMessageCreate(content="Il était une fois ", interrupted=True)
    turn.llm_msg_b = LLMMessageCreate(content="Un jour ", interrupted=True)
    comp.error = None
    comp.revealed = False

    cleared: list = []

    async def update_comparison_error(comparison, error=None):
        comparison.error = error

    async def clear_turn_answers(id):
        cleared.append(id)

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/arena/retry",
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": ("10.0.0.1", 1234),
        }
    )
    with patched(
        router,
        update_comparison_error=update_comparison_error,
        clear_turn_answers=clear_turn_answers,
        store_comparison_metadata=lambda id, is_streaming: None,
    ):
        # The body streams the models and is never consumed here.
        asyncio.run(router.retry(comp, "b" * 64, request))

    assert turn.llm_msg_a is None and turn.llm_msg_b is None
    assert streaming._get_messages(comp, "a")[-1] is turn.user_msg
    # Cleared in the database as well: update_turn leaves a None side alone,
    # so a retry stopped before its first word would keep the old answer.
    assert cleared == [turn.id]


if __name__ == "__main__":
    test_a_stop_is_recorded_while_streaming_and_kept_with_the_same_ttl()
    test_a_stop_after_the_answers_landed_changes_nothing()
    test_starting_the_next_turn_clears_a_stale_stop()
    test_a_stop_closes_both_streams_and_keeps_the_partial_answers()
    test_a_side_that_finished_before_the_stop_is_not_flagged()
    test_without_a_stop_the_stream_ends_as_before()
    test_a_cut_answer_with_text_is_completed_and_flagged()
    test_a_cut_answer_without_text_is_dropped()
    test_the_route_saves_the_cut_answers_and_sends_them_back()
    test_the_owner_can_stop_and_gets_204_even_when_nothing_streams()
    test_someone_else_cannot_stop_a_comparison()
    test_a_retry_drops_the_stopped_answers_from_the_transcript()
    print("Stop cases passed.")
