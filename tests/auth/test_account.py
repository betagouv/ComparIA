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

import backend.auth.export as auth_export  # noqa: E402
import backend.auth.router as auth_router  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.auth.dependencies import require_user  # noqa: E402
from utils.database.models.auth import ConsentLog, User  # noqa: E402
from utils.database.models.comparison import Comparison  # noqa: E402
from utils.database.models.messages import LLMMessage, UserMessage  # noqa: E402
from utils.database.models.turn import Turn  # noqa: E402


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


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    """Collects the statements a service runs so a test can replay them."""

    def __init__(self, user=None, *results):
        self.user = user
        self.results = list(results)
        self.statements = []
        self.committed = False

    async def get(self, _model, _id):
        return self.user

    async def exec(self, _statement):
        return FakeResult(self.results.pop(0) if self.results else [])

    async def execute(self, statement):
        self.statements.append(statement)

    def add(self, _value):
        pass

    async def commit(self):
        self.committed = True


@contextlib.contextmanager
def fake_session(session, module=auth_services):
    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    with patched(module, get_session=get_session):
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


def turn_of(comparison_id):
    turn = Turn(
        comparison_id=comparison_id,
        choice="a_better",
        keyword_annotations_a=["utile"],
        custom_annotation_a="la réponse la plus claire",
    )
    turn.user_msg = UserMessage(content="Explique la photosynthèse")
    turn.llm_msg_a = LLMMessage(
        content="Réponse A",
        created_at=datetime.now(),
        responded_at=datetime.now(),
        updated_at=datetime.now(),
        generation_id="gen-a",
        tokens=12,
        is_cached=False,
    )
    turn.llm_msg_b = None
    return turn


def test_public_config_carries_the_deployment_url():
    """The accessibility declaration names the domain it applies to."""

    async def get_app_settings():
        return SimpleNamespace(
            auth_access_policy="anonymous_first",
            auth_domain_allowlist=[],
            platform_name="Arène de test",
            primary_color_light="#000091",
            primary_color_dark="#8585F6",
            secondary_color_light="#6A6AF4",
            secondary_color_dark="#CACAFB",
            homepage_url=None,
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


def export_of(user, comparison, consents=(), model_names=()):
    session = FakeSession(user, [comparison], list(consents), list(model_names))
    with fake_session(session, auth_export):
        return asyncio.run(auth_export.build_account_export(user))


def test_export_carries_the_conversations_and_the_consent_history():
    user = User(email="personne@example.org")
    comparison = comparison_of(user.id)
    comparison.turns = [turn_of(comparison.id)]
    consent = ConsentLog(
        user_id=user.id,
        terms_version="2026.07",
        document_hash="a" * 64,
        language="fr",
        consented_at=datetime(2026, 7, 1, 9, 30),
        ip="not_collected",
    )

    export = export_of(user, comparison, consents=[consent])

    assert export.account.email == "personne@example.org"
    assert [
        (record.terms_version, record.document_hash, record.locale, record.accepted_at)
        for record in export.consents
    ] == [("2026.07", "a" * 64, "fr", datetime(2026, 7, 1, 9, 30))]
    conversation = export.conversations[0]
    assert conversation.accepted_terms_version == comparison.participation_terms_version
    turn = conversation.turns[0]
    assert turn.prompt == "Explique la photosynthèse"
    assert turn.response_a.content == "Réponse A"
    assert turn.response_b is None
    assert turn.choice == "a_better"
    assert turn.keyword_annotations_a == ["utile"]


def test_export_names_the_models_only_once_the_comparison_is_revealed():
    user = User(email="personne@example.org")
    comparison = comparison_of(user.id)
    names = [(comparison.llm_id_a, "modele-a"), (comparison.llm_id_b, "modele-b")]

    hidden = export_of(user, comparison, model_names=names)
    assert (hidden.conversations[0].model_a, hidden.conversations[0].model_b) == (
        None,
        None,
    )

    comparison.revealed = True
    revealed = export_of(user, comparison, model_names=names)
    assert (revealed.conversations[0].model_a, revealed.conversations[0].model_b) == (
        "modele-a",
        "modele-b",
    )


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
