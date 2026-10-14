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

import pytest  # noqa: E402
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
        id=uuid4(),
        user_msg=SimpleNamespace(content="Bonjour"),
        llm_msg_a=answer,
        llm_msg_b=answer,
    )
    return SimpleNamespace(
        id=uuid4(),
        turns=[turn],
        error=error,
        mode="random",
        llm_id_a="a",
        llm_id_b="b",
    )


def retry(target, expensive_available=True, drain=False, **patches):
    async def nothing(*_args, **_kwargs):
        return None

    async def get_llms_data():
        return SimpleNamespace(expensive_models=[])

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
            get_llms_data=get_llms_data,
            follow_up_sent=lambda _comparison: {},
            charge_turn=lambda *_args, **_kwargs: SimpleNamespace(
                settle=lambda _answers: None
            ),
            read_status=lambda _who: SimpleNamespace(
                expensive_available=expensive_available
            ),
            **patches,
        ),
    ):
        body = arena_models.RetryBody(altcha_token="valid")

        async def call():
            response = await arena_router.retry(target, body, "b" * 64, request)
            # The response streams the models, which most tests never read.
            # Those that do read it here, while the stand-ins still hold.
            if drain:
                [_ async for _ in response.body_iterator]
            return response

        return asyncio.run(call())


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


@pytest.mark.parametrize("expensive_available", [True, False])
def test_a_retry_hands_the_stand_in_whether_an_expensive_model_may_answer(
    expensive_available,
):
    """The swap at the start and the swap while streaming both follow what is
    left of the person's expensive allowance."""
    swaps = []
    streamed = []

    async def pick_replacement_model(_comparison, _pos, expensive_available):
        swaps.append(expensive_available)
        return "c"

    async def stream_comparison_messages(
        _comparison, _turn, _request, available, _charge
    ):
        streamed.append(available)
        return
        yield

    async def nothing(*_args, **_kwargs):
        return None

    failed = comparison(
        answered=False, error=SimpleNamespace(pos="a", is_timeout=False)
    )
    response = retry(
        failed,
        expensive_available=expensive_available,
        drain=True,
        pick_replacement_model=pick_replacement_model,
        update_comparison_llm_id=nothing,
        stream_comparison_messages=stream_comparison_messages,
        TurnPublic=SimpleNamespace(model_validate=lambda _turn: None),
        format_sse_event=lambda _event: "",
    )

    assert response.status_code == 200
    assert swaps == [expensive_available]
    assert streamed == [expensive_available]


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
