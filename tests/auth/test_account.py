"""
Unit tests for the account settings endpoints (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/auth/test_account.py
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.auth.router as auth_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.dependencies import require_user  # noqa: E402
from utils.database.models.auth import User  # noqa: E402
from utils.database.models.comparison import Comparison  # noqa: E402


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


class FakeSession:
    """Collects the statements a service runs so a test can replay them."""

    def __init__(self, user=None):
        self.user = user
        self.statements = []
        self.committed = False

    async def get(self, _model, _id):
        return self.user

    async def execute(self, statement):
        self.statements.append(statement)

    def add(self, _value):
        pass

    async def commit(self):
        self.committed = True


@contextlib.contextmanager
def fake_session(session):
    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    with patched(auth_services, get_session=get_session):
        yield session


def apply_updates(statements, table_name, row):
    """Replay the updates aimed at a table onto an in-memory row."""
    for statement in statements:
        if statement.is_update and statement.table.name == table_name:
            columns = {column.name for column in statement.table.columns}
            for name, value in statement.compile().params.items():
                if name in columns:
                    setattr(row, name, value)


def deleted_tables(statements):
    return {statement.table.name for statement in statements if statement.is_delete}


@contextlib.contextmanager
def signed_in(user):
    app = FastAPI()
    app.include_router(auth_router.router)
    app.dependency_overrides[require_user] = lambda: user
    yield TestClient(app)


def comparison_of(user_id):
    return Comparison(
        ip="192.0.2.10",
        visitor_id="matomo-visitor",
        anonymous_user_hash="c" * 64,
        user_id=user_id,
        mode="random",
        llm_id_a=uuid.uuid4(),
        llm_id_b=uuid.uuid4(),
    )


def test_public_config_carries_the_deployment_url():
    """The accessibility declaration names the domain it applies to."""

    async def get_app_settings():
        return SimpleNamespace(
            auth_access_policy="anonymous_first",
            auth_domain_allowlist=[],
            platform_name="Arène de test",
            logo=None,
        )

    with patched(auth_router, get_app_settings=get_app_settings):
        with patched(
            auth_router.settings, COMPARIA_APP_URL="https://arene.example.test"
        ):
            config = asyncio.run(auth_router.get_config())

    assert config.platform_url == "https://arene.example.test"


def test_erasure_leaves_no_identifier_on_the_comparisons():
    user = User(email="personne@example.test")
    comparison = comparison_of(user.id)
    session = FakeSession(user)

    with fake_session(session):
        asyncio.run(auth_services.erase_user_account(user.id))

    apply_updates(session.statements, "comparison", comparison)

    assert comparison.user_id is None
    assert comparison.visitor_id is None
    assert comparison.anonymous_user_hash is None
    assert comparison.ip == auth_services.ERASED_IP


def test_erasure_anonymises_the_account_and_clears_its_credentials():
    user = User(email="personne@example.test")
    session = FakeSession(user)

    with fake_session(session):
        asyncio.run(auth_services.erase_user_account(user.id))

    assert session.committed
    assert user.deleted_at is not None
    assert user.email == f"deleted-{user.id}@deleted.invalid"
    assert deleted_tables(session.statements) == {
        "auth_login_code",
        "auth_invite_token",
    }


def test_erasure_keeps_the_consent_proof_without_its_address():
    user = User(email="personne@example.test")
    session = FakeSession(user)

    with fake_session(session):
        asyncio.run(auth_services.erase_user_account(user.id))

    consent_updates = [
        statement
        for statement in session.statements
        if statement.is_update and statement.table.name == "auth_consent_log"
    ]
    assert len(consent_updates) == 1
    assert consent_updates[0].compile().params["ip"] == auth_services.ERASED_IP
    assert "auth_consent_log" not in deleted_tables(session.statements)


def test_erasure_needs_the_signed_in_address_and_drops_the_session_cookie():
    user = User(email="Personne@example.org")
    erased = []

    async def erase_user_account(user_id):
        erased.append(user_id)

    with patched(auth_router, erase_user_account=erase_user_account):
        with signed_in(user) as test_client:
            refused = test_client.request(
                "DELETE", "/auth/me", json={"email": "autre@example.org"}
            )
            accepted = test_client.request(
                "DELETE", "/auth/me", json={"email": "personne@example.org"}
            )

    assert refused.status_code == 400
    assert erased == [user.id]
    assert accepted.status_code == 204
    assert "auth_session" in accepted.headers.get("set-cookie", "")


def test_erasure_is_not_replayed_on_an_already_erased_account():
    user = User(email="deleted@deleted.invalid", deleted_at=datetime.now())
    session = FakeSession(user)

    with fake_session(session):
        asyncio.run(auth_services.erase_user_account(user.id))

    assert session.statements == []
    assert not session.committed


if __name__ == "__main__":
    for name, test in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            test()
