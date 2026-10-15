"""
The limits as admin settings: a stored value wins over the env default, each
process reads them again after a while, and the arena reads them before each
route (no database, no real Redis).
"""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

import backend.arena.limits as limits
import backend.arena.router as arena_router
import backend.arena.turn_limits as turn_limits
from backend.arena.limits import AllowanceSpent, Identity
from backend.config import settings
from tests.arena.fakes import fake_redis
from utils.database.models.app_settings import AppSettings

WHO = Identity.of("sess-a", "1.1.1.1")


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    """Each test starts with nothing stored and nothing read yet."""
    monkeypatch.setattr(limits, "_stored", {})
    monkeypatch.setattr(limits, "_loaded_at", None)


def stored(**values):
    """What get_app_settings hands back, with these limits stored."""
    reads = []

    async def get_app_settings():
        reads.append(1)
        return AppSettings(**{f"limit_{name}": v for name, v in values.items()})

    get_app_settings.reads = reads
    return get_app_settings


def test_a_stored_value_wins_over_the_default(monkeypatch):
    monkeypatch.setattr(limits, "get_app_settings", stored(all_per_session=1234))
    asyncio.run(limits.load_settings())

    assert limits.setting("all_per_session") == 1234
    assert limits.limit("all", "session") == 1234
    # The others stay on their env default, and follow it.
    monkeypatch.setattr(settings, "RATELIMIT_ALL_PER_IP", 777)
    assert limits.setting("all_per_ip") == 777


def test_a_stored_zero_is_kept_rather_than_read_as_unset(monkeypatch):
    monkeypatch.setattr(limits, "get_app_settings", stored(expected_answer_chars=0))
    asyncio.run(limits.load_settings())
    assert limits.setting("expected_answer_chars") == 0


def test_the_settings_are_read_again_only_after_a_while(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(limits.time, "monotonic", lambda: clock[0])
    get_app_settings = stored(all_per_session=10)
    monkeypatch.setattr(limits, "get_app_settings", get_app_settings)

    asyncio.run(limits.reload_settings())
    clock[0] += limits.RELOAD_SECONDS - 1
    asyncio.run(limits.reload_settings())
    assert len(get_app_settings.reads) == 1

    # Another pod stored a new value meanwhile: it is read once the time is up.
    monkeypatch.setattr(limits, "get_app_settings", stored(all_per_session=20))
    clock[0] += 1
    asyncio.run(limits.reload_settings())
    assert limits.setting("all_per_session") == 20


def test_a_failed_read_keeps_the_last_values(monkeypatch):
    monkeypatch.setattr(limits, "get_app_settings", stored(all_per_session=10))
    asyncio.run(limits.load_settings())

    async def broken():
        raise ConnectionError("database down")

    monkeypatch.setattr(limits, "get_app_settings", broken)
    asyncio.run(limits.load_settings())
    assert limits.setting("all_per_session") == 10


def test_a_message_is_refused_at_the_stored_limit(monkeypatch):
    monkeypatch.setattr(
        limits, "get_app_settings", stored(expensive_per_session=0.0001)
    )
    asyncio.run(limits.load_settings())
    with fake_redis(limits):
        limits.reserve(WHO, {"all": 101, "expensive": 101})
        with pytest.raises(AllowanceSpent) as refusal:
            limits.reserve(WHO, {"all": 1, "expensive": 1})
    [spent] = refusal.value.spent
    # 0.0001 dollars, in millionths.
    assert (spent.pool, spent.scope, spent.limit) == ("expensive", "session", 100)


def test_dollars_stay_dollars_and_characters_whole(monkeypatch):
    monkeypatch.setattr(
        limits,
        "get_app_settings",
        stored(expensive_per_ip=12.5, expensive_price_out=9.99, all_per_ip=5000),
    )
    asyncio.run(limits.load_settings())

    assert limits.setting("expensive_per_ip") == 12.5
    assert limits.limit("expensive", "ip") == 12_500_000
    assert limits.setting("expensive_price_out") == 9.99
    assert limits.limit("all", "ip") == 5000


def test_the_stored_threshold_decides_which_models_are_expensive(monkeypatch):
    sonnet = SimpleNamespace(price_in=2.6, price_out=13.0)
    assert limits.is_expensive(sonnet)

    monkeypatch.setattr(limits, "get_app_settings", stored(expensive_price_out=20))
    asyncio.run(limits.load_settings())
    assert not limits.is_expensive(sonnet)


def test_every_arena_route_reads_the_settings_first():
    assert [d.dependency for d in arena_router.router.dependencies] == [
        limits.reload_settings
    ]


def test_a_turn_reserves_the_stored_expected_answer(monkeypatch):
    monkeypatch.setattr(limits, "_stored", {"expected_answer_chars": 42})

    a, b = uuid4(), uuid4()
    priced = SimpleNamespace(price_in=1.0, price_out=2.0)
    data = SimpleNamespace(all={a: priced, b: priced})

    calls = turn_limits.turn_calls({"a": (a, 10), "b": (b, 20)}, data)
    assert [call.written for call in calls.values()] == [42, 42]
