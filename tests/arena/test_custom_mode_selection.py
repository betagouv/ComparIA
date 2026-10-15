"""
Manual mode with no model picked (no DB, no Redis).

The arena used to accept `mode=custom` with an empty selection, draw two random
models, and store the comparison as `custom`. It is now stored as `random`.

Run with pytest, or directly:
    uv run python tests/arena/test_custom_mode_selection.py
"""

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402

import backend.arena.models as arena_models  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
from tests.arena.test_participation_gate import arena, patched  # noqa: E402


def body(**kwargs):
    with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
        return arena_models.AddFirstTextBody(
            prompt_value="Bonjour, explique la photosynthese",
            cohorts="",
            altcha_token="valid",
            **kwargs,
        )


def send_first_message(args):
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/arena/add_first_text",
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": ("10.0.0.1", 1234),
        }
    )
    try:
        asyncio.run(arena_router.add_first_text(args, None, "b" * 64, request))
    except HTTPException as error:
        # The stubbed `create_comparison` stops the request once it has the row.
        assert error.status_code == 503


def test_custom_mode_without_models_is_random():
    for selection in ([], None):
        args = body(mode="custom", custom_models_selection=selection)
        assert args.mode == "random"
        assert args.custom_models_selection is None


def test_custom_mode_with_models_is_kept():
    llm_id = str(uuid4())
    args = body(mode="custom", custom_models_selection=[llm_id])
    assert args.mode == "custom"
    assert args.custom_models_selection == (llm_id,)


def test_custom_mode_without_models_is_stored_as_random():
    with arena(None) as created:
        send_first_message(body(mode="custom", custom_models_selection=[]))

    assert len(created) == 1
    assert created[0].mode == "random"
    assert created[0].custom_models_selection is None


if __name__ == "__main__":
    test_custom_mode_without_models_is_random()
    test_custom_mode_with_models_is_kept()
    test_custom_mode_without_models_is_stored_as_random()
