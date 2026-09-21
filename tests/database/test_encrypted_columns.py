"""
The column types that keep stored secrets encrypted (no DB).

Run with pytest, or directly:
    uv run python tests/database/test_encrypted_columns.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

import pytest  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402
from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlmodel import select  # noqa: E402

import utils.database.models  # noqa: E402,F401 registers every table
from utils.database.encrypted import (  # noqa: E402
    EncryptedJSONFields,
    EncryptedStr,
    looks_encrypted,
)
from utils.database.models.publish import (  # noqa: E402
    SECRET_FIELDS,
    PublishDestination,
)
from utils.secrets import decrypt_secret  # noqa: E402


def token_from_a_lost_key(plain: str = "x") -> str:
    return Fernet(Fernet.generate_key()).encrypt(plain.encode()).decode()


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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
