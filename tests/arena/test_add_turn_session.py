"""
A turn's session must be closed by the time `add_comparison_turn` returns. Read
after the block, it opens a new transaction nobody closes, and the connection
stays out of the pool until the garbage collector drops it.
"""

import asyncio
import contextlib
import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import backend.arena.services as services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing services


class FakeSession:
    def __init__(self):
        self.closed = False

    def add(self, _item):
        pass

    async def exec(self, _statement):
        pass

    async def commit(self):
        pass


def test_the_new_turn_is_read_before_the_session_closes(monkeypatch):
    session = FakeSession()
    turn_id = {}

    @contextlib.asynccontextmanager
    async def get_session():
        yield session
        session.closed = True

    async def get_item(_class, _id, used):
        assert not used.closed, "read on a session that is already closed"
        return SimpleNamespace()

    def validate_turn(turn):
        turn_id["id"] = uuid4()
        return SimpleNamespace(id=turn_id["id"])

    monkeypatch.setattr(services, "get_session", get_session)
    monkeypatch.setattr(services, "_get_item", get_item)
    monkeypatch.setattr(services, "TurnCreate", lambda **_kwargs: None)
    monkeypatch.setattr(services, "UserMessage", lambda **_kwargs: None)
    monkeypatch.setattr(services, "Turn", SimpleNamespace(model_validate=validate_turn))
    monkeypatch.setattr(
        services,
        "ComparisonRead",
        SimpleNamespace(
            model_validate=lambda _item: SimpleNamespace(
                turns=[SimpleNamespace(id=turn_id["id"])]
            )
        ),
    )

    asyncio.run(services.add_comparison_turn(uuid4(), "Bonjour"))
    assert session.closed
