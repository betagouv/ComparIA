"""
A first message naming a model the visitor may no longer pick.

An admin can lock a model out of custom mode, or turn it off, while a tab
still lists it. The arena then gets a known `detail` it can explain, not a 500.
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402

import backend.arena.models as arena_models  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.llms.data import LLMsData  # noqa: E402
from backend.llms.models import LLMDataEnabled  # noqa: E402
from tests.arena.test_ratelimit import default_prompt_check  # noqa: E402

OPEN = uuid4()
LOCKED = uuid4()


class FakeSession:
    async def exec(self, _statement):
        return type("Result", (), {"first": lambda self: None})()


@pytest.fixture(autouse=True)
def arena(monkeypatch: pytest.MonkeyPatch) -> None:
    def llm(id, custom_selectable):
        return LLMDataEnabled.model_construct(
            id=id, status="enabled", params=10, custom_selectable=custom_selectable
        )

    models = [llm(OPEN, True), llm(LOCKED, False), llm(uuid4(), True)]
    llms = LLMsData.model_construct(all={model.id: model for model in models})

    async def get_llms_data():
        return llms

    @contextlib.asynccontextmanager
    async def get_session():
        yield FakeSession()

    async def get_active_legal_document(_kind, _language):
        return None

    async def run_checks(*_args, **_kwargs):
        return None

    async def create_comparison(_comparison):
        raise HTTPException(status_code=503, detail="stop here")

    monkeypatch.setattr(arena_models, "verify_altcha_token", lambda _t: (True, None))
    monkeypatch.setattr(auth_services, "get_session", get_session)
    monkeypatch.setattr(
        auth_services, "get_active_legal_document", get_active_legal_document
    )
    monkeypatch.setattr(arena_router, "run_checks", run_checks)
    monkeypatch.setattr(arena_router, "get_llms_data", get_llms_data)
    monkeypatch.setattr(arena_router, "get_prompt_check", default_prompt_check)
    monkeypatch.setattr(arena_router, "create_comparison", create_comparison)
    monkeypatch.setattr(arena_router, "charge_budget", lambda *_args: None)
    monkeypatch.setattr(
        arena_router, "reserve_conversation", lambda *_args, **_kwargs: True
    )
    monkeypatch.setattr(arena_router, "release_conversation", lambda *_args: None)


def send_first_message(selection: tuple[str, ...]) -> HTTPException:
    body = arena_models.AddFirstTextBody(
        prompt_value="Bonjour, explique la photosynthese",
        mode="custom",
        custom_models_selection=selection,
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
    with pytest.raises(HTTPException) as error:
        asyncio.run(arena_router.add_first_text(body, None, "b" * 64, request))
    return error.value


@pytest.mark.parametrize("selection", [(str(LOCKED),), (str(uuid4()), str(OPEN))])
def test_a_model_nobody_may_pick_gets_a_known_detail(
    selection: tuple[str, ...],
) -> None:
    error = send_first_message(selection)
    assert (error.status_code, error.detail) == (400, "model_unavailable")


def test_an_open_model_goes_on_to_the_comparison() -> None:
    assert send_first_message((str(OPEN),)).status_code == 503
