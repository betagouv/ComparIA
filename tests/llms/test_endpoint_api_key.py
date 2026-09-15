"""The endpoint key must not reach the browser, and must survive a form save."""

import asyncio
import uuid

import pytest

from utils.database.models.llms import (
    LLMEndpoint,
    LLMEndpointPublic,
    LLMEndpointUpsert,
)
from utils.llms.services import clear_llm_endpoint_api_key, upsert_llm_endpoint


class FakeSession:
    def __init__(self, stored: LLMEndpoint | None = None):
        self.stored = stored
        self.added: list = []
        self.committed = False

    async def get(self, _model, _id):
        return self.stored

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def refresh(self, _item):
        return None


def endpoint(**overrides) -> LLMEndpoint:
    return LLMEndpoint(
        **{
            "id": uuid.uuid4(),
            "name": "OpenRouter",
            "api_type": "openrouter",
            "api_key": "sk-real-key",
            **overrides,
        }
    )


def test_the_public_shape_has_no_key_field():
    assert "api_key" not in LLMEndpointPublic.model_fields
    assert "has_api_key" in LLMEndpointPublic.model_fields


def test_a_save_without_a_key_keeps_the_stored_one():
    """The panel is not told the key, so a form round trip carries an empty one.
    Writing that through would disable every LLM on the endpoint."""
    stored = endpoint()
    session = FakeSession(stored)

    asyncio.run(
        upsert_llm_endpoint(
            LLMEndpointUpsert(id=stored.id, name="OpenRouter", api_type="openrouter"),
            session,  # type: ignore[arg-type]
        )
    )

    assert session.added[0].api_key == "sk-real-key"


@pytest.mark.parametrize("blank", ["", None])
def test_a_blank_key_is_not_a_clear(blank):
    stored = endpoint()
    session = FakeSession(stored)

    asyncio.run(
        upsert_llm_endpoint(
            LLMEndpointUpsert(
                id=stored.id, name="OpenRouter", api_type="openrouter", api_key=blank
            ),
            session,  # type: ignore[arg-type]
        )
    )

    assert session.added[0].api_key == "sk-real-key"


def test_a_new_key_replaces_the_stored_one():
    stored = endpoint()
    session = FakeSession(stored)

    asyncio.run(
        upsert_llm_endpoint(
            LLMEndpointUpsert(
                id=stored.id,
                name="OpenRouter",
                api_type="openrouter",
                api_key="sk-new-key",
            ),
            session,  # type: ignore[arg-type]
        )
    )

    assert session.added[0].api_key == "sk-new-key"


def test_clearing_is_explicit():
    stored = endpoint()
    session = FakeSession(stored)

    cleared = asyncio.run(clear_llm_endpoint_api_key(stored.id, session))  # type: ignore[arg-type]

    assert cleared is not None
    assert cleared.api_key is None
    assert session.committed


def test_clearing_an_unknown_endpoint_returns_none():
    session = FakeSession(None)

    assert asyncio.run(clear_llm_endpoint_api_key(uuid.uuid4(), session)) is None  # type: ignore[arg-type]
