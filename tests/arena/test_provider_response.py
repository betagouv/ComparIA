"""
Unit tests for finding the HTTP response behind a litellm stream (no provider).

Run with pytest, or directly:
    uv run python tests/arena/test_provider_response.py
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import httpx  # noqa: E402

from backend.arena.litellm import _provider_response  # noqa: E402


def response() -> httpx.Response:
    return httpx.Response(200, request=httpx.Request("POST", "https://x/y"))


def test_the_openai_sdk_stream_keeps_the_response_on_itself():
    http = response()
    wrapper = SimpleNamespace(completion_stream=SimpleNamespace(response=http))
    assert _provider_response(cast(Any, wrapper)) is http


def test_a_litellm_handler_keeps_only_the_line_iterator():
    class Reader:
        def __init__(self, http):
            self.http = http

        async def lines(self):
            # `self` is what the frame of httpx's aiter_lines holds too.
            yield "data: 1"

    http = response()
    reader = Reader(http)
    gen = reader.lines()
    # A wrapper whose response is held by the generator's own object, the
    # way httpx's Response.aiter_lines holds it: not found, since only an
    # httpx.Response in the frame counts.
    wrapper = SimpleNamespace(completion_stream=SimpleNamespace(streaming_response=gen))
    assert _provider_response(cast(Any, wrapper)) is None

    # The real thing: httpx's own line iterator over a streaming response.
    wrapper = SimpleNamespace(
        completion_stream=SimpleNamespace(streaming_response=http.aiter_lines())
    )
    assert _provider_response(cast(Any, wrapper)) is http


def test_a_mock_stream_has_nothing_to_close():
    wrapper = SimpleNamespace(completion_stream=SimpleNamespace())
    assert _provider_response(cast(Any, wrapper)) is None


if __name__ == "__main__":
    test_the_openai_sdk_stream_keeps_the_response_on_itself()
    test_a_litellm_handler_keeps_only_the_line_iterator()
    test_a_mock_stream_has_nothing_to_close()
    print("Provider response cases passed.")
