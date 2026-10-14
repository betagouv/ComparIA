import asyncio
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ["COMPARIA_DB_URI"] = "postgresql://comparia:comparia@localhost/comparia"
os.environ["LOG_FORMAT"] = "JSON"

from starlette.requests import Request  # noqa: E402

import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.arena import reveal  # noqa: E402
from backend.arena import router as arena_router  # noqa: E402


def test_count_input_tokens_counts_prompt_history():
    calls: list[list[str]] = []

    def fake_token_counter(text: list[str], model: str) -> int:
        calls.append(text)
        return len(text)

    comparison = SimpleNamespace(
        system_msg_a="system",
        turns=[
            SimpleNamespace(
                user_msg=SimpleNamespace(content="first question"),
                llm_msg_a=SimpleNamespace(
                    reasoning_content=None,
                    content="first answer",
                ),
            ),
            SimpleNamespace(
                user_msg=SimpleNamespace(content="second question"),
                llm_msg_a=SimpleNamespace(
                    reasoning_content="second reasoning",
                    content="second answer",
                ),
            ),
        ],
    )

    original_token_counter = reveal.token_counter
    reveal.token_counter = fake_token_counter
    try:
        assert (
            reveal.count_input_tokens(comparison, "a", comparison.turns, "model") == 6
        )
        assert calls == [
            ["system", "first question"],
            ["system", "first question", "first answer", "second question"],
        ]
    finally:
        reveal.token_counter = original_token_counter


def test_revealing_a_long_conversation_leaves_the_loop_free(monkeypatch):
    """
    Counting the tokens of a maxed-out conversation takes seconds of CPU.
    Every other visitor waits if that runs on the event loop.
    """
    work = 0.6

    def slow_reveal_data(comparison, llms):
        time.sleep(work)
        return {"b64": "", "chosen_llm": None}

    async def set_comparison_revealed(_comparison_id):
        pass

    async def get_llms_data():
        return SimpleNamespace()

    monkeypatch.setattr(arena_router, "get_reveal_data", slow_reveal_data)
    monkeypatch.setattr(
        arena_router, "set_comparison_revealed", set_comparison_revealed
    )
    monkeypatch.setattr(arena_router, "get_llms_data", get_llms_data)

    comparison: Any = SimpleNamespace(
        id=uuid4(), revealed=False, turns=[SimpleNamespace(choice="a_better")]
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/arena/reveal",
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": ("10.0.0.1", 1234),
        }
    )

    async def scenario():
        longest = 0.0
        done = asyncio.Event()

        async def heartbeat():
            nonlocal longest
            last = time.monotonic()
            while not done.is_set():
                await asyncio.sleep(0.01)
                now = time.monotonic()
                longest = max(longest, now - last)
                last = now

        beat = asyncio.create_task(heartbeat())
        await asyncio.sleep(0.05)
        data = await arena_router.reveal(comparison, request)
        done.set()
        await beat
        return longest, data

    stall, data = asyncio.run(scenario())
    assert data == {"b64": "", "chosen_llm": None}
    assert stall < 0.25, f"event loop stalled for {stall:.2f}s"


def run():
    test_count_input_tokens_counts_prompt_history()
    print("Reveal token counting cases passed.")


if __name__ == "__main__":
    run()
