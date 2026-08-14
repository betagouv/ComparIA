"""
Unit tests for the cap on how long one comparison can run (no DB, no Redis).

Every turn resends the whole transcript to both models, so the cost of a
conversation grows with its square and something has to stop it.

Run with pytest, or directly:
    uv run python tests/arena/test_turn_cap.py
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
from starlette.requests import Request  # noqa: E402

import backend.arena.models as arena_models  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.config import MAX_TURNS_PER_COMPARISON  # noqa: E402


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


def comparison_with(turn_count: int):
    return SimpleNamespace(id=uuid4(), turns=[object()] * turn_count)


def send_follow_up(comparison):
    async def run_checks(_text, _field, _request, _warning_token):
        return None

    body = arena_models.AddTextBody(
        message="Et pour les plantes en hiver, comment cela se passe ?",
        altcha_token="valid",
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/arena/add_text",
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": ("10.0.0.1", 1234),
        }
    )
    with patched(arena_router, run_checks=run_checks):
        # The body of the response streams the models, which these tests never
        # consume, so nothing here reaches the database.
        return asyncio.run(arena_router.add_text(comparison, body, "b" * 64, request))


def test_a_conversation_below_the_cap_goes_through():
    with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
        response = send_follow_up(comparison_with(MAX_TURNS_PER_COMPARISON - 1))
    assert response.status_code == 200


def test_a_conversation_at_the_cap_is_refused():
    with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
        try:
            send_follow_up(comparison_with(MAX_TURNS_PER_COMPARISON))
        except HTTPException as error:
            assert error.status_code == 403
            # The frontend shows `detail`, so it has to say something a reader
            # can act on.
            assert str(MAX_TURNS_PER_COMPARISON) in error.detail
        else:
            raise AssertionError("a comparison grew past the cap")


def test_the_cap_is_not_a_ceiling_that_can_be_stepped_over():
    """A transcript already past the cap (an older row, a raised then lowered
    setting) must not be allowed to keep growing."""
    with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
        try:
            send_follow_up(comparison_with(MAX_TURNS_PER_COMPARISON + 5))
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("an over-long comparison grew further")


if __name__ == "__main__":
    test_a_conversation_below_the_cap_goes_through()
    test_a_conversation_at_the_cap_is_refused()
    test_the_cap_is_not_a_ceiling_that_can_be_stepped_over()
    print("Turn cap cases passed.")
