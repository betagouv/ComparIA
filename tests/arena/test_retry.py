"""
Unit tests for when a turn can be run again (no DB, no Redis).

A retry answers the same prompt again without running the prompt check, so it
is only open to a turn that failed or never finished, and it costs a captcha
like any other message.

Run with pytest, or directly:
    uv run python tests/arena/test_retry.py
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

from fastapi import HTTPException  # noqa: E402
from pydantic import ValidationError  # noqa: E402
from starlette.requests import Request  # noqa: E402

import backend.arena.models as arena_models  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
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


def comparison(answered: bool, error=None):
    answer = object() if answered else None
    turn = SimpleNamespace(
        id=uuid4(), user_msg=object(), llm_msg_a=answer, llm_msg_b=answer
    )
    return SimpleNamespace(id=uuid4(), turns=[turn], error=error, mode="random")


def retry(target):
    async def nothing(*_args, **_kwargs):
        return None

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
    with (
        patched(arena_models, verify_altcha_token=lambda _token: (True, None)),
        patched(
            arena_router,
            update_comparison_error=nothing,
            store_comparison_metadata=lambda *_args, **_kwargs: None,
        ),
    ):
        body = arena_models.RetryBody(altcha_token="valid")
        # The response streams the models, which these tests never consume.
        return asyncio.run(arena_router.retry(target, body, "b" * 64, request))


def test_a_finished_turn_cannot_be_answered_again():
    try:
        retry(comparison(answered=True))
    except HTTPException as error:
        assert error.status_code == 400
        assert error.detail == "retry_unavailable"
    else:
        raise AssertionError("a finished turn was run again")


def test_a_turn_that_never_finished_can_be_retried():
    assert retry(comparison(answered=False)).status_code == 200


def test_a_failed_turn_can_be_retried():
    failed = comparison(answered=True, error=SimpleNamespace(pos=None))
    assert retry(failed).status_code == 200


def test_a_retry_needs_a_captcha():
    with patched(arena_models, verify_altcha_token=lambda _token: (False, "bad")):
        try:
            arena_models.RetryBody(altcha_token="replayed")
        except ValidationError as error:
            assert "captcha_failed" in str(error)
        else:
            raise AssertionError("a retry went through without a captcha")


if __name__ == "__main__":
    test_a_finished_turn_cannot_be_answered_again()
    test_a_turn_that_never_finished_can_be_retried()
    test_a_failed_turn_can_be_retried()
    test_a_retry_needs_a_captcha()
    print("Retry cases passed.")
