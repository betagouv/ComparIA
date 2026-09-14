import os

# The app refuses to start without an Altcha key outside debug, so that a
# deployment cannot silently run with a per-process one. Tests are not a
# deployment: give them a fixed key before anything imports backend.config.
os.environ.setdefault("ALTCHA_HMAC_KEY", "test-altcha-hmac-key")
# Same for the authenticator secret key: any valid Fernet key will do.
os.environ.setdefault(
    "AUTH_TOTP_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
)


import asyncio  # noqa: E402
import glob  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402

import pytest  # noqa: E402


def _postgres_bin() -> str | None:
    """Where initdb and pg_ctl live, on a developer machine or a CI runner."""
    found = shutil.which("initdb")
    if found:
        return os.path.dirname(found)
    for pattern in ("/usr/lib/postgresql/*/bin", "/opt/postgresql*/bin"):
        candidates = sorted(glob.glob(pattern))
        if candidates:
            return candidates[-1]
    return None


@pytest.fixture(scope="session")
def postgres_uri():
    """
    A throwaway Postgres cluster on a unix socket, with the schema created.
    For the tests whose subject is what lands in the database, or what the
    database can do, like advisory locks. Skipped where Postgres is not
    installed.
    """
    bin_dir = _postgres_bin()
    if bin_dir is None:
        pytest.skip("Postgres is not installed")

    # A short path: a unix socket path is limited to about a hundred bytes.
    data = tempfile.mkdtemp(prefix="pg", dir="/tmp")
    subprocess.run(
        [f"{bin_dir}/initdb", "-D", f"{data}/data", "-A", "trust", "-U", "test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            f"{bin_dir}/pg_ctl",
            "-D",
            f"{data}/data",
            "-o",
            f"-k {data} -c listen_addresses='' -c fsync=off",
            "-l",
            f"{data}/log",
            "-w",
            "start",
        ],
        check=True,
        # Not a pipe: the server inherits it, and the call then never returns.
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        subprocess.run(
            [f"{bin_dir}/createdb", "-h", data, "-U", "test", "comparia"],
            check=True,
            capture_output=True,
        )
        uri = f"postgresql://test@/comparia?host={data}"

        from sqlalchemy import create_engine
        from sqlmodel import SQLModel

        # Every table, or create_all cannot resolve the foreign keys.
        import utils.database.models  # noqa: F401
        import utils.database.models.auth  # noqa: F401
        import utils.database.models.llms  # noqa: F401
        import utils.database.models.messages  # noqa: F401
        import utils.database.models.prompt_check  # noqa: F401
        import utils.database.models.suggestion  # noqa: F401

        engine = create_engine(uri.replace("postgresql://", "postgresql+psycopg://"))
        SQLModel.metadata.create_all(engine)
        engine.dispose()
        yield uri
    finally:
        subprocess.run(
            [f"{bin_dir}/pg_ctl", "-D", f"{data}/data", "-m", "immediate", "stop"],
            capture_output=True,
        )
        shutil.rmtree(data, ignore_errors=True)


@pytest.fixture
def database(postgres_uri, monkeypatch):
    """
    Points the app's engine at the throwaway cluster and gives back a runner
    for async scenarios: each starts with empty tables, and its engine dies
    with its event loop.
    """
    from sqlalchemy import create_engine, text
    from sqlmodel import SQLModel

    from backend.config import settings
    from utils.database import session

    monkeypatch.setattr(settings, "COMPARIA_DB_URI", postgres_uri)
    monkeypatch.setattr(session, "_engine", None)
    monkeypatch.setattr(session, "_export_client", False)

    engine = create_engine(
        postgres_uri.replace("postgresql://", "postgresql+psycopg://")
    )
    with engine.begin() as connection:
        tables = ", ".join(
            f'"{table.name}"' for table in SQLModel.metadata.sorted_tables
        )
        connection.execute(text(f"TRUNCATE {tables} CASCADE"))
    engine.dispose()

    def run(scenario):
        async def wrapped():
            try:
                return await scenario()
            finally:
                if session._engine is not None:
                    await session._engine.dispose()
                    session._engine = None

        return asyncio.run(wrapped())

    return run
