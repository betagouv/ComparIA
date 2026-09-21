"""
The column types that keep stored secrets encrypted, and what the readers
and the key rotation do with a secret no configured key opens (no DB).

Run with pytest, or directly:
    uv run python tests/database/test_encrypted_columns.py
"""

import asyncio
import contextlib
import logging
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import pytest  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlmodel import select  # noqa: E402

import utils.database.models  # noqa: E402,F401 registers every table
import utils.database.secrets as secrets_check  # noqa: E402
from backend.admin.llms.router import _to_endpoint_public  # noqa: E402
from backend.arena.checks import moderate  # noqa: E402
from backend.llms.data import LLMsData  # noqa: E402
from utils.database.encrypted import (  # noqa: E402
    EncryptedJSONFields,
    EncryptedStr,
    UnreadableSecret,
    looks_encrypted,
)
from utils.database.models.auth import UserTotp  # noqa: E402
from utils.database.models.llms import LLMEndpoint  # noqa: E402
from utils.database.models.prompt_check import PromptCheck  # noqa: E402
from utils.database.models.publish import (  # noqa: E402
    SECRET_FIELDS,
    AdminPublishDestination,
    PublishDestination,
)
from utils.secrets import SecretUnreadableError, decrypt_secret  # noqa: E402


def token_from_a_lost_key(plain: str = "x") -> str:
    return Fernet(Fernet.generate_key()).encrypt(plain.encode()).decode()


def endpoint(api_key) -> LLMEndpoint:
    return LLMEndpoint(
        id=uuid.uuid4(), name="OpenRouter", api_type="openrouter", api_key=api_key
    )


def destination(config: dict) -> PublishDestination:
    return PublishDestination(
        id=uuid.uuid4(),
        name="open data",
        kind=config["kind"],
        config=config,
        datasets=["normal"],
    )


# The column types


def test_a_string_column_stores_a_token_and_reads_the_value_back():
    column = EncryptedStr()
    stored = column.process_bind_param("sk-secret", None)
    assert stored != "sk-secret"
    assert looks_encrypted(stored)
    assert decrypt_secret(stored) == "sk-secret"
    assert column.process_result_value(stored, None) == "sk-secret"


@pytest.mark.parametrize("empty", [None, ""])
def test_nothing_is_not_encrypted(empty):
    column = EncryptedStr()
    assert column.process_bind_param(empty, None) == empty
    assert column.process_result_value(empty, None) == empty


def test_only_the_secret_fields_of_a_config_are_encrypted():
    column = EncryptedJSONFields(SECRET_FIELDS)
    config = {
        "kind": "s3",
        "bucket": "open-data",
        "access_key": "AK",
        "secret_key": "SK",
    }

    stored = column.process_bind_param(config, None)
    assert stored["bucket"] == "open-data"
    assert looks_encrypted(stored["access_key"])
    assert looks_encrypted(stored["secret_key"])
    assert config["access_key"] == "AK", "the caller's dict is left alone"

    assert column.process_result_value(stored, None) == config


def test_an_unknown_kind_is_stored_as_is():
    column = EncryptedJSONFields(SECRET_FIELDS)
    config = {"kind": "ftp", "password": "p"}
    assert column.process_bind_param(config, None) == config


def test_looks_encrypted_tells_tokens_from_plain_values():
    assert looks_encrypted(EncryptedStr().process_bind_param("x", None))
    assert looks_encrypted(token_from_a_lost_key(""))
    assert not looks_encrypted("sk-plain")
    assert not looks_encrypted(None)
    # The prefix alone is not enough: a token is base64 and never short.
    assert not looks_encrypted("gAAAAA-short")
    assert not looks_encrypted("gAAAAA" + "!" * 100)
    assert not looks_encrypted("gAAAAA" + "A" * 93)


def test_a_json_lookup_on_the_encrypted_column_compiles_and_caches():
    """The type's arguments are part of SQLAlchemy's statement cache key,
    which has to be hashable."""
    statement = select(PublishDestination).where(
        PublishDestination.config["kind"].astext == "s3"
    )
    assert "config ->>" in str(statement.compile(dialect=postgresql.dialect()))
    # The CacheKey wrapper is unhashable by design; the executor hashes .key.
    assert hash(statement._generate_cache_key().key)

    same = EncryptedJSONFields(dict(reversed(list(SECRET_FIELDS.items()))))
    assert same.secret_fields == EncryptedJSONFields(SECRET_FIELDS).secret_fields


# A secret no configured key opens


def test_an_unreadable_string_reads_as_a_marker_not_as_nothing():
    token = token_from_a_lost_key()
    value = EncryptedStr().process_result_value(token, None)

    assert isinstance(value, UnreadableSecret)
    assert value, "a key is set, it just cannot be read"
    with pytest.raises(SecretUnreadableError):
        str(value)
    with pytest.raises(SecretUnreadableError):
        f"Bearer {value}"


def test_an_unreadable_marker_writes_its_token_back_unchanged():
    token = token_from_a_lost_key()
    column = EncryptedStr()
    assert (
        column.process_bind_param(column.process_result_value(token, None), None)
        == token
    )


def test_an_unreadable_config_field_keeps_the_rest_readable_and_round_trips():
    column = EncryptedJSONFields(SECRET_FIELDS)
    stored = {
        "kind": "huggingface",
        "repo_path": "org/repo",
        "token": token_from_a_lost_key(),
    }

    loaded = column.process_result_value(stored, None)
    assert loaded["repo_path"] == "org/repo"
    assert isinstance(loaded["token"], UnreadableSecret)

    assert column.process_bind_param(loaded, None) == stored


def test_the_loader_disables_the_endpoint_it_cannot_read_and_names_it(caplog):
    bad = endpoint(UnreadableSecret(token_from_a_lost_key()))
    good = endpoint("sk-fine")
    llms = [
        SimpleNamespace(id=uuid.uuid4(), status="enabled", endpoint=bad),
        SimpleNamespace(id=uuid.uuid4(), status="enabled", endpoint=bad),
        SimpleNamespace(id=uuid.uuid4(), status="enabled", endpoint=good),
        SimpleNamespace(id=uuid.uuid4(), status="enabled", endpoint=endpoint(None)),
        SimpleNamespace(id=uuid.uuid4(), status="archived", endpoint=None),
    ]

    with caplog.at_level(logging.ERROR, logger="languia"):
        kept = LLMsData.filter_disabled(llms)

    assert list(kept) == [llms[2].id, llms[4].id]
    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1, "once per endpoint, not per model"
    assert f"llm_endpoint {bad.id}.api_key" in errors[0]
    assert "OpenRouter" in errors[0]


def test_the_admin_panel_still_says_a_key_is_set():
    public = _to_endpoint_public(endpoint(UnreadableSecret(token_from_a_lost_key())))
    assert public.has_api_key is True
    assert "api_key" not in public.model_dump()


def test_moderation_fails_rather_than_sending_the_marker():
    with pytest.raises(SecretUnreadableError, match="prompt_check 1.api_key"):
        asyncio.run(moderate("hi", "m", UnreadableSecret(token_from_a_lost_key())))


def test_a_destination_names_itself_when_its_credentials_cannot_be_read():
    row = destination(
        {
            "kind": "s3",
            "endpoint": "s3.example",
            "bucket": "b",
            "access_key": UnreadableSecret(token_from_a_lost_key()),
            "secret_key": "SK",
        }
    )
    with pytest.raises(SecretUnreadableError, match=f"{row.id}.config.access_key"):
        row.parsed_config()
    # The panel lists it all the same: the public shape has no secret.
    assert AdminPublishDestination.from_row(row).config.bucket == "b"


# The startup check


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    """Answers each `select(model)` with the rows given for that model."""

    def __init__(self, **rows_by_table):
        self.rows_by_table = rows_by_table
        self.statements = []
        self.added = []
        self.commits = 0

    async def exec(self, statement):
        self.statements.append(statement)
        table = statement.get_final_froms()[0].name
        return FakeResult(self.rows_by_table.get(table, []))

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1


@contextlib.contextmanager
def fake_session(session, *modules):
    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    originals = {module: module.get_session for module in modules}
    for module in modules:
        module.get_session = get_session
    try:
        yield session
    finally:
        for module, original in originals.items():
            module.get_session = original


def totp(secret_token, pending_token=None) -> UserTotp:
    return UserTotp(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        secret_encrypted=secret_token,
        pending_secret_encrypted=pending_token,
    )


def test_the_startup_check_names_every_unreadable_row_and_changes_nothing(caplog):
    lost = token_from_a_lost_key()
    bad_endpoint = endpoint(UnreadableSecret(lost))
    bad_destination = destination(
        {"kind": "huggingface", "repo_path": "o/r", "token": UnreadableSecret(lost)}
    )
    bad_totp = totp(EncryptedStr().process_bind_param("ok", None), lost)
    session = FakeSession(
        llm_endpoint=[endpoint("sk-fine"), bad_endpoint, endpoint(None)],
        prompt_check=[PromptCheck(id=1, api_key="sk-fine")],
        publish_destination=[bad_destination],
        auth_totp=[bad_totp],
    )

    with (
        fake_session(session, secrets_check),
        caplog.at_level(logging.ERROR, logger="comparia.db"),
    ):
        unreadable = asyncio.run(secrets_check.log_unreadable_secrets())

    assert [str(ref) for ref in unreadable] == [
        f"llm_endpoint {bad_endpoint.id}.api_key",
        f"publish_destination {bad_destination.id}.config.token",
        f"auth_totp {bad_totp.id}.pending_secret_encrypted",
    ]
    messages = [r.getMessage() for r in caplog.records if r.name == "comparia.db"]
    assert len(messages) == 3, "one per row, on top of the decrypt's own line"
    assert all(str(ref) in msg for ref, msg in zip(unreadable, messages))
    assert lost not in "".join(messages)
    assert session.added == [] and session.commits == 0
    assert all(s._for_update_arg is None for s in session.statements)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
