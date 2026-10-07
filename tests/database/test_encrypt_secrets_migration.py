"""
The secrets migration, upgrade and downgrade, against an in-memory stand-in
for the three tables it rewrites (no DB).

Run with pytest, or directly:
    uv run python tests/database/test_encrypt_secrets_migration.py
"""

import copy
import importlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402

from utils.secrets import decrypt_secret, encrypt_secret  # noqa: E402

migration = importlib.import_module(
    "utils.database.alembic.versions.c3e7a9b2d4f6_encrypt_stored_secrets"
)

SELECT = re.compile(r"SELECT id, (\w+) FROM (\w+)( WHERE \w+ IS NOT NULL)?")
UPDATE = re.compile(r"UPDATE (\w+) SET (\w+) = ")


class Result:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class Connection:
    """Answers the migration's SELECTs and UPDATEs from `tables`, a dict of
    table -> id -> row. A config comes back as a JSON string, as it can from
    the driver."""

    def __init__(self, tables):
        self.tables = tables
        self.updates = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        if match := SELECT.match(sql):
            column, table, not_null = match.groups()
            rows = [
                (row_id, row[column])
                for row_id, row in self.tables[table].items()
                if not (not_null and row[column] is None)
            ]
            if column == "config":
                rows = [(row_id, json.dumps(value)) for row_id, value in rows]
            return Result(rows)
        match = UPDATE.match(sql)
        assert match, sql
        table, column = match.groups()
        value = params.get("value", params.get("config"))
        if column == "config":
            value = json.loads(value)
        self.tables[table][params["id"]][column] = value
        self.updates += 1
        return Result([])


class Operations:
    def __init__(self, connection):
        self.connection = connection

    def get_bind(self):
        return self.connection


def run(step, tables) -> Connection:
    connection = Connection(tables)
    original = migration.op
    migration.op = Operations(connection)
    try:
        step()
    finally:
        migration.op = original
    return connection


def plain_tables():
    return {
        "llm_endpoint": {1: {"api_key": "sk-a"}, 2: {"api_key": None}},
        "prompt_check": {1: {"api_key": "sk-m"}},
        "publish_destination": {
            1: {
                "config": {
                    "kind": "s3",
                    "bucket": "open-data",
                    "access_key": "AK",
                    "secret_key": "SK",
                }
            },
            2: {"config": {"kind": "huggingface", "repo_path": "o/r", "token": "t"}},
            3: {"config": {"kind": "ftp", "password": "p"}},
        },
    }


def test_upgrade_encrypts_only_the_secrets():
    tables = plain_tables()
    run(migration.upgrade, tables)

    assert decrypt_secret(tables["llm_endpoint"][1]["api_key"]) == "sk-a"
    assert tables["llm_endpoint"][2]["api_key"] is None
    assert decrypt_secret(tables["prompt_check"][1]["api_key"]) == "sk-m"
    s3 = tables["publish_destination"][1]["config"]
    assert s3["bucket"] == "open-data"
    assert decrypt_secret(s3["access_key"]) == "AK"
    assert decrypt_secret(s3["secret_key"]) == "SK"
    hf = tables["publish_destination"][2]["config"]
    assert hf["repo_path"] == "o/r"
    assert decrypt_secret(hf["token"]) == "t"
    assert tables["publish_destination"][3]["config"] == {
        "kind": "ftp",
        "password": "p",
    }


def test_upgrade_run_twice_changes_nothing_the_second_time():
    tables = plain_tables()
    run(migration.upgrade, tables)
    once = copy.deepcopy(tables)

    connection = run(migration.upgrade, tables)

    assert connection.updates == 0
    assert tables == once


def test_downgrade_gives_back_the_plain_values():
    tables = plain_tables()
    run(migration.upgrade, tables)
    run(migration.downgrade, tables)
    assert tables == plain_tables()


def test_downgrade_refuses_a_secret_no_key_opens():
    lost = Fernet(Fernet.generate_key()).encrypt(b"sk-a").decode()
    tables = {
        "llm_endpoint": {1: {"api_key": lost}},
        "prompt_check": {},
        "publish_destination": {},
    }
    with pytest.raises(RuntimeError, match="before downgrading"):
        run(migration.downgrade, tables)


def test_the_heuristic_tells_tokens_from_plain_values():
    looks_encrypted = migration._looks_encrypted
    assert looks_encrypted(encrypt_secret("x"))
    assert looks_encrypted(Fernet(Fernet.generate_key()).encrypt(b"").decode())
    assert not looks_encrypted("sk-plain")
    assert not looks_encrypted(None)
    # The prefix alone is not enough: a token is base64 and never short.
    assert not looks_encrypted("gAAAAA-short")
    assert not looks_encrypted("gAAAAA" + "!" * 100)
    assert not looks_encrypted("gAAAAA" + "A" * 93)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
