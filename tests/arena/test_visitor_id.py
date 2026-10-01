"""
The audience measurement is exempt from consent only as long as its data is
not crossed with anything else, so a comparison must not keep the Matomo
visitor id the browser sends along (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/arena/test_visitor_id.py
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


def test_a_comparison_does_not_keep_the_matomo_visitor_id():
    created = []

    async def get_current_terms_acceptance_version(**_ids):
        return "2026.07"

    async def run_checks(_text, _field, _request, _warning_token):
        return None

    async def get_llms_data():
        return SimpleNamespace(pick_two=lambda _mode, _selection: (uuid4(), uuid4()))

    async def create_comparison(comparison):
        created.append(comparison)
        raise HTTPException(status_code=503, detail="stop here")

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/arena/add_first_text",
            "path_params": {},
            "query_string": b"",
            "headers": [(b"cookie", b"_pk_id.126.1fff=0123456789abcdef.1700000000.")],
            "client": ("10.0.0.1", 1234),
        }
    )

    with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
        body = arena_models.AddFirstTextBody(
            prompt_value="Bonjour, explique la photosynthese",
            cohorts="",
            altcha_token="valid",
        )
        with patched(
            arena_router,
            get_current_terms_acceptance_version=get_current_terms_acceptance_version,
            run_checks=run_checks,
            get_llms_data=get_llms_data,
            create_comparison=create_comparison,
        ):
            try:
                asyncio.run(arena_router.add_first_text(body, None, "b" * 64, request))
            except HTTPException as error:
                assert error.status_code == 503

    [comparison] = created
    assert comparison.visitor_id is None


if __name__ == "__main__":
    test_a_comparison_does_not_keep_the_matomo_visitor_id()
