import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("LOG_FORMAT", "JSON")

from backend.arena import reveal


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


def run():
    test_count_input_tokens_counts_prompt_history()
    print("Reveal token counting cases passed.")


if __name__ == "__main__":
    run()
