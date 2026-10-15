"""
A signed-in person counts on their account, with more room than a session
(no network, no DB, no real Redis).

The account's counters are not the session's: signing in starts them empty,
and signing out goes back to what the session had spent. Both personal pools,
whole and expensive, get the signed-in factor; the network ones stay as they
are, since a school is the same school signed in or not.
"""

import asyncio
import importlib
import os
from types import SimpleNamespace
from uuid import uuid4

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.arena.limits as limits  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.arena.limits import AllowanceSpent, Identity  # noqa: E402
from backend.auth.dependencies import optional_user, require_anonymous  # noqa: E402
from backend.config import settings  # noqa: E402
from tests.arena.fakes import fake_redis  # noqa: E402
from utils.database.models.app_settings import AppSettings  # noqa: E402

SESSION = "c" * 64
IP = "10.0.0.1"
USER = uuid4()
ANONYMOUS = Identity.of(SESSION, IP)
SIGNED_IN = Identity.of(SESSION, IP, USER)


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    """Nothing stored or read yet: every limit on its env default."""
    monkeypatch.setattr(limits, "_stored", {})
    monkeypatch.setattr(limits, "_loaded_at", None)


def test_signed_in_the_person_is_the_account_and_the_network_stays():
    assert SIGNED_IN.session == f"u:{USER}"
    assert SIGNED_IN.network == ANONYMOUS.network
    assert ANONYMOUS.session == f"s:{SESSION}"


def test_the_account_counter_is_not_the_session_counter():
    keys = {limits.budget_key(pool, SIGNED_IN.session) for pool in limits.POOLS}
    assert keys.isdisjoint(
        limits.budget_key(pool, ANONYMOUS.session) for pool in limits.POOLS
    )
    with fake_redis(limits):
        limits.reserve(ANONYMOUS, {"all": 500, "expensive": 70})

        # Signing in starts the account's counters empty...
        signed_in = {
            (a.pool, a.scope): a.used for a in limits.read_status(SIGNED_IN).allowances
        }
        assert signed_in[("all", "session")] == 0
        assert signed_in[("expensive", "session")] == 0
        # ...on the same network, which counted the session's message.
        assert signed_in[("all", "network")] == 500

        limits.reserve(SIGNED_IN, {"all": 200})

        # Signing out goes back to what the session had spent.
        anonymous = {
            (a.pool, a.scope): a.used for a in limits.read_status(ANONYMOUS).allowances
        }
        assert anonymous[("all", "session")] == 500
        assert anonymous[("all", "network")] == 700


def test_the_factor_applies_to_both_personal_pools_and_not_to_the_network():
    with fake_redis(limits):
        signed_in = {
            (a.pool, a.scope): a.limit for a in limits.read_status(SIGNED_IN).allowances
        }
        anonymous = {
            (a.pool, a.scope): a.limit for a in limits.read_status(ANONYMOUS).allowances
        }

    for pool in limits.POOLS:
        assert signed_in[(pool, "session")] == 3 * anonymous[(pool, "session")]
        assert signed_in[(pool, "network")] == anonymous[(pool, "network")]


def test_an_account_goes_on_past_the_session_limit_up_to_three_times_it():
    session_limit = limits.limit("all", "session")
    with fake_redis(limits):
        limits.reserve(SIGNED_IN, {"all": session_limit + 1}, refusing=())
        # Past what a session may send, an account still goes on.
        limits.reserve(SIGNED_IN, {"all": 1})
        limits.reserve(SIGNED_IN, {"all": 2 * session_limit}, refusing=())
        with pytest.raises(AllowanceSpent) as refusal:
            limits.reserve(SIGNED_IN, {"all": 1})

    [spent] = refusal.value.spent
    assert (spent.scope, spent.identity) == ("session", SIGNED_IN.session)
    assert spent.limit == 3 * session_limit


def test_the_factor_is_an_env_default_an_admin_can_change(monkeypatch):
    assert settings.RATELIMIT_SIGNED_IN_FACTOR == 3
    assert limits.default("signed_in_factor") == 3

    monkeypatch.setattr(settings, "RATELIMIT_SIGNED_IN_FACTOR", 2)
    assert limits.signed_in_factor() == 2
    expensive = limits.limit("expensive", "session")
    assert limits.identity_limit("expensive", SIGNED_IN.session) == 2 * expensive

    async def get_app_settings():
        return AppSettings(limit_signed_in_factor=4.5)

    monkeypatch.setattr(limits, "get_app_settings", get_app_settings)
    asyncio.run(limits.load_settings())

    assert limits.signed_in_factor() == 4.5
    whole = limits.limit("all", "session")
    assert limits.identity_limit("all", SIGNED_IN.session) == int(whole * 4.5)
    assert limits.identity_limit("all", SIGNED_IN.network) == limits.limit(
        "all", "network"
    )
    assert limits.identity_limit("all", ANONYMOUS.session) == whole


@pytest.fixture
def arena(monkeypatch):
    """GET /arena/limits against a fake Redis; `user` is who is signed in."""
    state = SimpleNamespace(user=None)

    async def get_llms_data():
        return SimpleNamespace(enabled={})

    async def signed_in():
        return state.user

    monkeypatch.setattr(arena_router, "get_llms_data", get_llms_data)
    app = FastAPI()
    app.include_router(arena_router.router)
    app.dependency_overrides[require_anonymous] = lambda: SESSION
    app.dependency_overrides[optional_user] = signed_in
    with fake_redis(limits) as redis:
        state.redis = redis
        state.client = TestClient(app)
        yield state


def spend(redis, identity):
    spent = limits.identity_limit("all", identity) + 1
    redis.set(limits.budget_key("all", identity), spent, ex=limits.WINDOW_SECONDS)


def test_the_limits_read_the_account_while_signed_in(arena):
    spend(arena.redis, f"s:{SESSION}")

    anonymous = arena.client.get("/arena/limits").json()
    assert anonymous["total"]["scope"] == "session"
    assert anonymous["signed_in_factor"] == 3

    arena.user = SimpleNamespace(id=USER)
    signed_in = arena.client.get("/arena/limits").json()
    # The session's spent allowance is not the account's.
    assert signed_in["total"] is None
    assert signed_in["signed_in_factor"] == 3

    spend(arena.redis, f"u:{USER}")
    assert arena.client.get("/arena/limits").json()["total"]["scope"] == "session"


def test_a_spent_network_is_spent_signed_in_too(arena):
    network = limits.network_identity("testclient")
    arena.redis.set(
        limits.budget_key("all", network),
        limits.limit("all", "network") + 1,
        ex=limits.WINDOW_SECONDS,
    )
    arena.user = SimpleNamespace(id=USER)

    assert arena.client.get("/arena/limits").json()["total"]["scope"] == "network"


class Operations:
    """Stands in for alembic's `op`, keeping what the migration asks for."""

    def __init__(self):
        self.added = []
        self.dropped = []

    def add_column(self, table, column):
        self.added.append((table, column))

    def drop_column(self, table, column):
        self.dropped.append((table, column))


def test_the_migration_adds_an_empty_factor_and_takes_it_back(monkeypatch):
    migration = importlib.import_module(
        "utils.database.alembic.versions."
        "5c8e2f71a9d4_add_signed_in_factor_to_app_settings"
    )
    operations = Operations()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()
    [(table, column)] = operations.added
    assert (table, column.name, column.nullable) == (
        "app_settings",
        "limit_signed_in_factor",
        True,
    )
    # Empty, so the env default holds until an admin sets one.
    assert column.server_default is None

    migration.downgrade()
    assert operations.dropped == [("app_settings", "limit_signed_in_factor")]
    assert migration.down_revision == "1bdbe90c7e4c"
