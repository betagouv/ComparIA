import os

# The app refuses to start without an Altcha key outside debug, so that a
# deployment cannot silently run with a per-process one. Tests are not a
# deployment: give them a fixed key before anything imports backend.config.
os.environ.setdefault("ALTCHA_HMAC_KEY", "test-altcha-hmac-key")
# Same for the authenticator secret key: any valid Fernet key will do.
os.environ.setdefault(
    "COMPARIA_ENCRYPTION_KEY",
    "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",  # gitleaks:allow
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
        # A connection the previous scenario left open, idle in a transaction,
        # would hold the lock the truncate below waits for.
        connection.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid()"
            )
        )
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


@pytest.fixture
def fake_redis(monkeypatch):
    """An in-memory Redis behind both the sync and the async client."""
    from tests.support import fake_redis as fake

    store = fake.install(monkeypatch)
    yield store
    fake.uninstall()


@pytest.fixture
def fake_provider():
    """A local model provider speaking the OpenAI streaming protocol."""
    from tests.support.fake_provider import FakeProvider

    provider = FakeProvider().start()
    yield provider
    provider.stop()


class Arena:
    """The arena HTTP API of the real app, with its models on a fake provider."""

    def __init__(self, client, provider, redis):
        self.client = client
        self.provider = provider
        self.redis = redis

    def ask(self, prompt: str = "Bonjour, explique la photosynthese", **body):
        """Post a first message and read the whole event stream it answers with."""
        response = self.client.post(
            "/api/arena/add_first_text",
            json={"prompt_value": prompt, "cohorts": "", "altcha_token": "ok", **body},
        )
        assert response.status_code == 200, response.text
        return parse_events(response.text)


def parse_events(text: str) -> list[dict]:
    import json

    return [
        json.loads(block[len("data: ") :])
        for block in text.split("\n\n")
        if block.startswith("data: ")
    ]


@pytest.fixture
def arena(database, fake_redis, fake_provider, monkeypatch):
    """
    The real app on a throwaway Postgres, two enabled models answering through
    the fake provider. What is not under test is out: the captcha and the
    prompt check, which would call the outside world.
    """
    import contextlib
    from datetime import date

    from fastapi.testclient import TestClient

    import backend.arena.models as arena_models
    import backend.arena.router as arena_router
    from backend.config import settings
    from backend.main import app
    from utils.database import session
    from utils.database import settings as app_settings
    from utils.database.models.llms import (
        LLMData,
        LLMEndpoint,
        LLMLab,
        LLMLicense,
    )

    # A developer's .env must not decide what the tests run against.
    monkeypatch.setattr(settings, "ADMIN_EMAILS", [])
    monkeypatch.setattr(app_settings._DEFAULTS, "auth_access_policy", "anonymous_first")

    async def no_check(_text, _field, _request, _warning_token=None):
        return None

    monkeypatch.setattr(
        arena_models, "verify_altcha_token", lambda _token: (True, None)
    )
    monkeypatch.setattr(arena_router, "run_checks", no_check)

    async def seed():
        async with session.get_session() as db:
            lab = LLMLab(name="Lab", logo=None, origin_country="FR")
            licence = LLMLicense(
                kind="open-source", name="MIT", reuse=True, commercial_use=True
            )
            endpoint = LLMEndpoint(
                name="fake",
                api_type="openai",
                api_base=fake_provider.base_url,
                api_key="test-key",
            )
            db.add_all([lab, licence, endpoint])
            await db.flush()
            for name in ("alpha", "beta"):
                db.add(
                    LLMData(
                        status="enabled",
                        name=name,
                        human_id=name,
                        api_model_id=name,
                        endpoint_id=endpoint.id,
                        rate_limited=False,
                        lab_id=lab.id,
                        release_date=date(2025, 1, 1),
                        knowledge_cutoff=None,
                        license_id=licence.id,
                        public_weights=True,
                        public_training_data=False,
                        public_training_code=False,
                        eu_hostable=True,
                        arch="dense",
                        params=7.0,
                        active_params=None,
                        context_tokens=8192,
                        quantization=None,
                        inputs=["text"],
                        price_in=0.1,
                        price_out=0.2,
                        system_prompt=None,
                    )
                )
            await db.commit()

    database(seed)

    with TestClient(app) as client:
        yield Arena(client, fake_provider, fake_redis)
        engine = session._engine
        if engine is not None:
            client.portal.call(engine.dispose)
            session._engine = None
