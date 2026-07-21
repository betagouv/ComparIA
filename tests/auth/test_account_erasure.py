import asyncio
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.auth import services
from utils.database.models.auth import User


class FakeSession:
    def __init__(self, user: User):
        self.user = user
        self.statements = []
        self.committed = False

    async def get(self, _model, _user_id):
        return self.user

    async def execute(self, statement):
        self.statements.append(statement)

    def add(self, _value):
        pass

    async def commit(self):
        self.committed = True


def test_account_erasure_anonymizes_identity_and_runs_all_cleanup(monkeypatch):
    user = User(id=uuid.uuid4(), email="personne@example.test")
    session = FakeSession(user)

    @asynccontextmanager
    async def fake_get_session():
        yield session

    monkeypatch.setattr(services, "get_session", fake_get_session)

    asyncio.run(services.erase_user_account(user.id))

    assert session.committed
    assert user.deleted_at is not None
    assert user.email == f"deleted-{user.id}@deleted.invalid"
    assert len(session.statements) == 6
