"""
Unit tests for the terms gate on the first arena message (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/arena/test_participation_gate.py
"""

import asyncio
import contextlib
import os
import sys
from datetime import datetime
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
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from utils.database.models.auth import LegalDocument  # noqa: E402
from utils.database.models.comparison import (  # noqa: E402
    LEGACY_PARTICIPATION_TERMS_VERSION,
)

DOCUMENT = LegalDocument(
    kind="terms",
    version="2026.07",
    language="fr",
    content="Conditions publiées",
    content_hash="a" * 64,
    effective_at=datetime(2026, 7, 1),
)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    async def exec(self, _statement):
        return FakeResult([])


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


@contextlib.contextmanager
def arena(active_document):
    """Run add_first_text against stubs, capturing the comparison it creates."""
    created = []

    async def get_session():
        yield FakeSession()

    async def get_active_legal_document(_kind, _language):
        return active_document

    async def run_checks(_text, _field, _request, _warning_token):
        return None

    async def get_llms_data():
        return SimpleNamespace(pick_two=lambda _mode, _selection: (uuid4(), uuid4()))

    async def create_comparison(comparison):
        created.append(comparison)
        # The response streams the models, which is not what these tests check.
        raise HTTPException(status_code=503, detail="stop here")

    with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
        with patched(
            auth_services,
            get_session=contextlib.asynccontextmanager(get_session),
            get_active_legal_document=get_active_legal_document,
        ):
            with patched(
                arena_router,
                run_checks=run_checks,
                get_llms_data=get_llms_data,
                create_comparison=create_comparison,
            ):
                yield created


def send_first_message():
    body = arena_models.AddFirstTextBody(
        prompt_value="Bonjour, explique la photosynthese",
        cohorts="",
        altcha_token="valid",
    )
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
    return asyncio.run(arena_router.add_first_text(body, None, "b" * 64, request))


def test_a_first_message_needs_the_terms_in_force_to_be_accepted():
    with arena(DOCUMENT) as created:
        try:
            send_first_message()
        except HTTPException as error:
            assert error.status_code == 428
        else:
            raise AssertionError("an unaccepted first message was let through")
    assert created == []


def test_a_first_message_is_not_gated_when_nothing_is_published():
    """A fresh instance must stay usable until an administrator publishes."""
    with arena(None) as created:
        try:
            send_first_message()
        except HTTPException as error:
            assert error.status_code == 503, "the gate rejected the message"

    assert len(created) == 1
    assert created[0].participation_terms_version == LEGACY_PARTICIPATION_TERMS_VERSION


if __name__ == "__main__":
    test_a_first_message_needs_the_terms_in_force_to_be_accepted()
    test_a_first_message_is_not_gated_when_nothing_is_published()
