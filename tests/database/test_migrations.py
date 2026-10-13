"""
The whole migration chain against an empty database, the way a new instance
or a fresh developer checkout runs it. The other database tests build their
schema with create_all, so a migration that only breaks on an empty database
would go unnoticed.
"""

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]


def _alembic(uri: str, *args: str) -> None:
    env = {
        **os.environ,
        "COMPARIA_DB_URI": uri,
        # f8c2b6a41d70 seeds the instance locale and refuses to guess it.
        "COMPARIA_INSTANCE_NAME": "fr",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr[-3000:]


def test_upgrade_downgrade_upgrade_on_empty_database(postgres_uri):
    host = parse_qs(urlparse(postgres_uri).query)["host"][0]
    admin = create_engine(
        postgres_uri.replace("postgresql://", "postgresql+psycopg://"),
        isolation_level="AUTOCOMMIT",
    )
    with admin.connect() as connection:
        connection.execute(text("DROP DATABASE IF EXISTS migrations"))
        connection.execute(text("CREATE DATABASE migrations"))
    admin.dispose()

    uri = f"postgresql://test@/migrations?host={host}"
    _alembic(uri, "upgrade", "head")
    _alembic(uri, "downgrade", "base")
    _alembic(uri, "upgrade", "head")
