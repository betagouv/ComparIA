"""
The limits module on its own: where the allowances come from, what a status
reads back, and the operator's reset (no network, no real Redis).
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest

import backend.arena.limits as limits
from backend.arena.limits import AllowanceSpent, Identity
from backend.config import Settings, settings
from tests.arena.fakes import fake_redis
from utils.arena.actions import limits_reset, limits_show
from utils.storage.redis import REDIS_INSTANCE_PREFIX

WHO = Identity.of("sess-a", "1.1.1.1")


def allowance(status, pool, scope):
    [found] = [a for a in status.allowances if (a.pool, a.scope) == (pool, scope)]
    return found


def test_an_env_var_sets_an_allowance(monkeypatch):
    monkeypatch.setenv("RATELIMIT_EXPENSIVE_PER_SESSION", "2000")
    assert Settings().RATELIMIT_EXPENSIVE_PER_SESSION == 2000


def test_the_allowances_keep_their_numbers():
    assert settings.RATELIMIT_EXPENSIVE_PER_SESSION == 100_000
    assert settings.RATELIMIT_EXPENSIVE_PER_IP == 5_000_000
    assert settings.RATELIMIT_ALL_PER_SESSION == 500_000
    assert settings.RATELIMIT_ALL_PER_IP == 10_000_000


def test_the_counters_keep_the_keys_they_had_before_the_module():
    # A deploy must not hand everyone their allowances back.
    assert limits.budget_key("expensive", WHO.personal) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:pricey:sess-a"
    )
    assert limits.budget_key("expensive", WHO.network) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:pricey_ip:1.1.1.1"
    )
    assert limits.budget_key("all", WHO.personal) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:all:sess-a"
    )
    assert limits.budget_key("all", WHO.network) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:all_ip:1.1.1.1"
    )


def test_a_lowered_allowance_refuses_at_its_new_limit(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 2000)
    with fake_redis(limits):
        limits.reserve(WHO, {"all": 2000, "expensive": 2000})
        limits.reserve(WHO, {"all": 1, "expensive": 1})
        with pytest.raises(AllowanceSpent) as refusal:
            limits.reserve(WHO, {"all": 1, "expensive": 1})
    assert [(a.pool, a.scope) for a in refusal.value.spent] == [
        ("expensive", "session")
    ]


def test_a_message_that_counts_for_nothing_still_meets_a_spent_allowance():
    # A lone invisible character passes the length check, then comes out
    # empty once hidden characters are stripped.
    with fake_redis(limits):
        limits.reserve(WHO, {"all": settings.RATELIMIT_ALL_PER_SESSION + 1})
        with pytest.raises(AllowanceSpent):
            limits.reserve(WHO, {"all": 0})


def test_a_cheap_pair_leaves_the_expensive_pool_out():
    cheap, expensive = uuid4(), uuid4()
    llms_data = SimpleNamespace(expensive_models=[expensive])
    assert limits.message_cost("abc", (cheap, cheap), llms_data) == {"all": 3}
    assert limits.message_cost("abc", (cheap, expensive), llms_data) == {
        "all": 3,
        "expensive": 3,
    }


def test_a_status_counts_down_to_the_reset():
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 10})
        redis.advance(600)
        status = limits.read_status(WHO)

    spent = allowance(status, "all", "session")
    assert (spent.used, spent.resets_in) == (10, limits.WINDOW_SECONDS - 600)
    untouched = allowance(status, "expensive", "session")
    assert (untouched.used, untouched.resets_in) == (0, None)
    assert status.spent == ()


def test_a_window_closes_after_two_quiet_hours():
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": settings.RATELIMIT_ALL_PER_SESSION + 1})
        assert limits.read_status(WHO).spent
        redis.advance(limits.WINDOW_SECONDS)
        assert not limits.read_status(WHO).spent


def test_a_refund_never_leaves_a_counter_without_expiry():
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": settings.RATELIMIT_ALL_PER_SESSION + 1})
        pipelines = []
        charge_then_refund = redis.pipeline

        def pipeline(transaction=True):
            pipelines.append(transaction)
            if len(pipelines) == 2:
                # The counters run out between the charge and the refund.
                redis.advance(limits.WINDOW_SECONDS)
            return charge_then_refund(transaction)

        redis.pipeline = pipeline
        with pytest.raises(AllowanceSpent):
            limits.reserve(WHO, {"all": 1})

        for identity in WHO.identities:
            assert redis.ttl(limits.budget_key("all", identity)) == (
                limits.WINDOW_SECONDS
            )
        redis.advance(limits.WINDOW_SECONDS)
        assert all(a.used == 0 for a in limits.read_status(WHO).allowances)


def test_a_reset_forgets_one_identity_only():
    other = Identity.of("sess-b", "2.2.2.2")
    with fake_redis(limits):
        limits.reserve(WHO, {"all": 10, "expensive": 10})
        limits.reserve(other, {"all": 10})
        assert limits.reset_counters([WHO.network]) == 2
        status = limits.read_status(WHO)
        assert allowance(status, "all", "session").used == 10
        assert allowance(status, "all", "ip").used == 0
        assert allowance(limits.read_status(other), "all", "ip").used == 10


def test_a_pool_that_may_not_refuse_is_still_charged(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 100)
    with fake_redis(limits):
        limits.reserve(WHO, {"all": 10, "expensive": 101})
        with pytest.raises(AllowanceSpent):
            limits.reserve(WHO, {"all": 10, "expensive": 10})
        limits.reserve(WHO, {"all": 10, "expensive": 10}, refusing=("all",))
        status = limits.read_status(WHO)

    assert allowance(status, "expensive", "session").used == 111
    assert allowance(status, "all", "session").used == 20
    assert not status.expensive_available


def test_a_spent_allowance_keeps_its_reset_time_while_it_is_charged(monkeypatch):
    """The person was told when the expensive models come back. A conversation
    that finishes over the spent allowance must not push that time back."""
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 100)
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 101, "expensive": 101})
        redis.advance(600)
        limits.reserve(WHO, {"all": 10, "expensive": 10}, refusing=("all",))
        status = limits.read_status(WHO)

    spent = allowance(status, "expensive", "session")
    assert spent.resets_in == limits.WINDOW_SECONDS - 600
    # The allowances with room left start their window again, as before.
    assert allowance(status, "all", "session").resets_in == limits.WINDOW_SECONDS
    assert allowance(status, "expensive", "ip").resets_in == limits.WINDOW_SECONDS


def test_the_cli_tells_a_counter_that_never_resets_from_none(caplog):
    with fake_redis(limits) as redis, caplog.at_level("INFO", "comparia.arena"):
        redis.set(limits.budget_key("all", WHO.personal), 10)
        redis.set(limits.budget_key("expensive", WHO.personal), 10, ex=61)
        limits_show(session="sess-a")
    assert "s:sess-a all: 10 of 500,000, never resets" in caplog.text
    assert "s:sess-a expensive: 10 of 100,000, resets in 2 min" in caplog.text


def test_the_cli_refuses_a_reset_with_no_one_to_reset(caplog):
    with fake_redis(limits), pytest.raises(SystemExit) as exit:
        limits_reset()
    assert exit.value.code == 1
    assert "Give --session, --ip or both." in caplog.text
