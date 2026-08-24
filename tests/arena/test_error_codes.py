"""
What a failed generation is allowed to say.

Provider error strings carry base URLs, provider names and often the model
itself, and they used to travel over SSE and into the comparison row, which the
public dataset then re-serves. Only a code goes now.

Run with pytest, or directly:
    uv run python tests/arena/test_error_codes.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import litellm  # noqa: E402

from backend.arena.streaming import error_code  # noqa: E402
from backend.errors import ContextTooLongError, EmptyResponseError  # noqa: E402

LEAKY = (
    "litellm.APIConnectionError: OpenAIException - Connection error to "
    "https://api.example-provider.com/v1 for model gpt-4o-mini"
)


def test_each_failure_maps_to_its_code():
    assert (
        error_code(litellm.Timeout(message=LEAKY, model="m", llm_provider="p"))
        == "timeout"
    )
    assert error_code(ContextTooLongError()) == "context_too_long"
    assert error_code(EmptyResponseError()) == "empty_response"


def test_an_unknown_failure_falls_back_to_the_generic_code():
    assert error_code(RuntimeError(LEAKY)) == "provider_error"


def test_no_code_repeats_anything_from_the_provider():
    for error in (RuntimeError(LEAKY), ValueError(LEAKY)):
        code = error_code(error)
        assert "example-provider" not in code
        assert "gpt-4o-mini" not in code


def run():
    test_each_failure_maps_to_its_code()
    test_an_unknown_failure_falls_back_to_the_generic_code()
    test_no_code_repeats_anything_from_the_provider()
    print("Error code cases passed.")


if __name__ == "__main__":
    run()
