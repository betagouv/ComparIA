"""
Unit tests for the merge of the two model streams (no DB, no Redis, no provider).

Each side is a fake async generator; the merge must forward every event, keep
one live task per side and end with the closing 'complete' event.

Run with pytest, or directly:
    uv run python tests/arena/test_streaming_merge.py
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.arena.streaming as streaming  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router


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


LLM_A, LLM_B = uuid4(), uuid4()


def comparison():
    turn = SimpleNamespace(
        id=uuid4(),
        user_msg=SimpleNamespace(content="Bonjour"),
        llm_msg_a=None,
        llm_msg_b=None,
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


def side(pos, chunks, delay, closed):
    """A model that says `chunks` one every `delay` seconds."""

    async def stream(pos_, llm, turn, turn_index, messages, request=None):
        assert pos_ == pos
        try:
            for chunk in chunks:
                await asyncio.sleep(delay)
                yield {"type": "chunk", "pos": pos, "llm_msg": chunk}
            yield {"type": "complete", "pos": pos}
        finally:
            closed.append(pos)

    return stream


def merge(sides):
    async def stream_llm_response(pos, *args, **kwargs):
        async for event in sides[pos](pos, *args, **kwargs):
            yield event

    async def run():
        comp, turn = comparison()
        with patched(
            streaming,
            stream_llm_response=stream_llm_response,
            get_llms_data=fake_llms_data,
        ):
            return [
                event
                async for event in streaming.stream_comparison_messages(comp, turn)
            ]

    return asyncio.run(run())


def test_events_arrive_in_time_order_and_nothing_is_lost():
    closed: list = []
    events = merge(
        {
            "a": side("a", ["a1", "a2"], 0.01, closed),
            "b": side("b", ["b1"], 0.04, closed),
        }
    )

    assert [(e["type"], e.get("pos")) for e in events] == [
        ("chunk", "a"),  # 10 ms
        ("chunk", "a"),  # 20 ms
        ("complete", "a"),  # 20 ms
        ("chunk", "b"),  # 40 ms
        ("complete", "b"),  # 40 ms
        ("complete", None),
    ]
    assert [e["llm_msg"] for e in events if e["type"] == "chunk"] == ["a1", "a2", "b1"]
    assert sorted(closed) == ["a", "b"]


def test_a_slow_side_is_not_cancelled_while_the_other_one_talks():
    """The old loop cancelled the pending anext() every iteration, which a real
    provider stream would not survive. A side that is thrown into must not
    reach its end."""
    thrown_into: list = []

    async def slow(pos, llm, turn, turn_index, messages, request=None):
        try:
            await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            thrown_into.append(pos)
            raise
        yield {"type": "chunk", "pos": pos, "llm_msg": "late"}
        yield {"type": "complete", "pos": pos}

    events = merge({"a": side("a", ["a1", "a2", "a3"], 0.01, []), "b": slow})

    assert thrown_into == []
    assert [e.get("llm_msg") for e in events if e["type"] == "chunk"] == [
        "a1",
        "a2",
        "a3",
        "late",
    ]


if __name__ == "__main__":
    test_events_arrive_in_time_order_and_nothing_is_lost()
    test_a_slow_side_is_not_cancelled_while_the_other_one_talks()
    print("Streaming merge cases passed.")
