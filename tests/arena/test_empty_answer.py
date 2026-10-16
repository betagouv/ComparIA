"""
A model that streams nothing back fails the turn with EmptyResponseError, the
error the stream turns into a message for the person (no network).
"""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

import backend.arena.conversation as conversation
from backend.arena.conversation import bot_response_async
from backend.errors import EmptyResponseError
from utils.database.models import UserMessageRead


def test_an_empty_answer_raises_empty_response_error(monkeypatch):
    async def litellm_stream_iter(llm, messages, msg, **_kwargs):
        msg.created_at = msg.updated_at = datetime.now()
        yield msg

    monkeypatch.setattr(conversation, "litellm_stream_iter", litellm_stream_iter)
    llm = SimpleNamespace(id="small-llm", api_model_id="small-2506")
    turn = SimpleNamespace(id=uuid4(), user_msg=UserMessageRead(content="Bonjour"))

    async def run():
        # A later turn, so the answer cache stays out of it.
        async for _msg in bot_response_async("a", llm, turn, 1, [turn.user_msg]):
            pass

    with pytest.raises(EmptyResponseError) as error:
        asyncio.run(run())
    assert "small-2506" in error.value.response
