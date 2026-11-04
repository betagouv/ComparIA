"""
The legal document migrations, run for real against an empty Postgres cluster.
Skipped where Postgres is not installed.
"""

import subprocess
import uuid
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]
STARTER_TERMS_ID = uuid.UUID("6f1b6f6e-8f4a-4c3e-9a2f-2d0d5a1f7b41")


@pytest.fixture
def migrate(postgres_uri, monkeypatch):
    """A fresh database, and a function that upgrades it to a revision."""
    from alembic import command
    from alembic.config import Config

    from backend.config import settings
    from tests.conftest import _postgres_bin

    host = postgres_uri.split("host=")[1]
    name = f"migrations_{uuid.uuid4().hex[:8]}"

    subprocess.run(
        [f"{_postgres_bin()}/createdb", "-h", host, "-U", "test", name],
        check=True,
        capture_output=True,
    )
    uri = f"postgresql://test@/{name}?host={host}"
    monkeypatch.setattr(settings, "COMPARIA_DB_URI", uri)
    # The default locale migration reads the environment, and CI has no .env.
    monkeypatch.setenv("COMPARIA_INSTANCE_NAME", "fr")

    # No ini file: the app's logging setup stays as the other tests expect it.
    config = Config()
    config.set_main_option("script_location", str(ROOT / "utils/database/alembic"))
    engine = create_engine(uri.replace("postgresql://", "postgresql+psycopg://"))

    def upgrade(revision: str = "head"):
        command.upgrade(config, revision)
        return engine

    yield upgrade
    engine.dispose()


def _insert_anonymous_consent(connection, document_id, document_hash, language):
    connection.execute(
        text("""
            INSERT INTO anonymous_consent_log (
                id, anonymous_user_hash, document_id, terms_version,
                document_hash, language, purpose, client_accepted_at, consented_at
            )
            VALUES (
                :id, :visitor, :document_id, 'v', :document_hash, :language,
                'terms_and_participation', :now, :now
            )
            """),
        {
            "id": uuid.uuid4(),
            "visitor": "a" * 64,
            "document_id": document_id,
            "document_hash": document_hash,
            "language": language,
            "now": datetime(2026, 1, 1),
        },
    )


def test_a_fresh_install_ships_no_terms(migrate):
    engine = migrate()

    with engine.connect() as connection:
        count = connection.execute(
            text("SELECT count(*) FROM legal_document WHERE kind = 'terms'")
        ).scalar_one()

    assert count == 0


def test_starter_terms_someone_accepted_are_kept(migrate):
    engine = migrate("e4a8c2d9f1b7")
    with engine.begin() as connection:
        starter_hash = connection.execute(
            text("SELECT content_hash FROM legal_document WHERE id = :id"),
            {"id": STARTER_TERMS_ID},
        ).scalar_one()
    migrate("d4f9a1c7e2b8")
    with engine.begin() as connection:
        _insert_anonymous_consent(connection, STARTER_TERMS_ID, starter_hash, "fr")

    migrate()

    with engine.connect() as connection:
        kept = connection.execute(
            text("SELECT count(*) FROM legal_document WHERE id = :id"),
            {"id": STARTER_TERMS_ID},
        ).scalar_one()
    assert kept == 1


def _insert_terms(connection, version, language, content, published_at):
    document_id = uuid.uuid4()
    connection.execute(
        text("""
            INSERT INTO legal_document (
                id, kind, version, language, content, content_hash,
                published_at, effective_at
            )
            VALUES (
                :id, 'terms', :version, :language, :content, :hash,
                :published_at, :published_at
            )
            """),
        {
            "id": document_id,
            "version": version,
            "language": language,
            "content": content,
            "hash": language * 32,
            "published_at": published_at,
        },
    )
    return document_id


def test_merging_translations_keeps_their_acceptances(migrate):
    engine = migrate("67fb732c509e")
    with engine.begin() as connection:
        french = _insert_terms(
            connection, "v1", "fr", "Conditions", datetime(2026, 1, 1)
        )
        english = _insert_terms(connection, "v1", "en", "Terms", datetime(2026, 1, 2))
        _insert_anonymous_consent(connection, english, "en" * 32, "en")

    migrate("0783a14a0418")

    with engine.connect() as connection:
        documents = connection.execute(
            text("SELECT id, content FROM legal_document WHERE version = 'v1'")
        ).all()
        accepted = connection.execute(
            text("SELECT document_id FROM anonymous_consent_log")
        ).scalar_one()
    assert [(row.id, row.content) for row in documents] == [
        (french, {"fr": "Conditions", "en": "Terms"})
    ]
    assert accepted == french
