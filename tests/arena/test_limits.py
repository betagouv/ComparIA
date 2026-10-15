"""
The limits module on its own: where the allowances come from, what a status
reads back, and the operator's reset (no network, no real Redis).
"""

import asyncio

import pytest
from redis.exceptions import RedisError, ResponseError

import backend.arena.limits as limits
import utils.storage.redis as redis_module
from backend.arena.limits import AllowanceSpent, Identity
from backend.config import Settings, settings
from tests.arena.fakes import FakeRedis, fake_redis
from utils.arena.actions import limits_reset, limits_show
from utils.database.models.app_settings import AppSettings
from utils.storage.redis import REDIS_INSTANCE_PREFIX

WHO = Identity.of("sess-a", "1.1.1.1")


async def no_stored_settings():
    return AppSettings()


def allowance(status, pool, scope):
    [found] = [a for a in status.allowances if (a.pool, a.scope) == (pool, scope)]
    return found


def test_an_env_var_sets_an_allowance(monkeypatch):
    monkeypatch.setenv("RATELIMIT_EXPENSIVE_PER_SESSION", "0.05")
    assert Settings().RATELIMIT_EXPENSIVE_PER_SESSION == 0.05


def test_the_allowances_have_their_defaults():
    assert settings.RATELIMIT_EXPENSIVE_PER_SESSION == 0.40
    assert settings.RATELIMIT_EXPENSIVE_PER_IP == 20.0
    assert settings.RATELIMIT_EXPENSIVE_PRICE_OUT == 8.0
    assert settings.RATELIMIT_ALL_PER_SESSION == 3_000_000
    assert settings.RATELIMIT_ALL_PER_IP == 60_000_000


def test_the_expensive_limits_count_in_millionths_of_a_dollar(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 0.4)
    assert limits.limit("expensive", "session") == 400_000
    assert limits.limit("all", "session") == settings.RATELIMIT_ALL_PER_SESSION


def test_the_whole_counters_keep_the_keys_they_had_before_the_module():
    # A deploy must not hand everyone their allowances back. The expensive
    # counters are new: the old ones held characters.
    assert limits.budget_key("expensive", WHO.personal) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:expensive_usd:sess-a"
    )
    assert limits.budget_key("expensive", WHO.network) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:expensive_usd_ip:1.1.1.1"
    )
    assert limits.budget_key("all", WHO.personal) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:all:sess-a"
    )
    assert limits.budget_key("all", WHO.network) == (
        f"{REDIS_INSTANCE_PREFIX}pricey_chars:all_ip:1.1.1.1"
    )


def test_a_lowered_allowance_refuses_at_its_new_limit(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 0.002)
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
    cheap = limits.Call(3, price_in=4.0, price_out=4.0)
    expensive = limits.Call(3, price_in=4.0, price_out=12.0, expensive=True)
    assert limits.turn_cost([cheap, cheap]) == {"all": 6}
    assert limits.turn_cost([cheap, expensive]) == {"all": 6, "expensive": 3}


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


def test_reading_the_limits_fails_open_and_charging_fails_closed():
    """With Redis down, nothing reads as spent, and a message is refused
    when it is charged, before any model is called."""
    with fake_redis(limits, fake=FakeRedis(pipelines_that_work=0)):
        assert limits.read_status(WHO).spent == ()
        with pytest.raises(RedisError):
            limits.reserve(WHO, {"all": 1})


def test_a_redis_out_of_reach_raises_what_the_limit_reads_catch(monkeypatch):
    def refused(_client):
        raise OSError("Connection refused")

    monkeypatch.setattr(redis_module.redis.Redis, "ping", refused)

    with pytest.raises(RedisError):
        redis_module.get_redis_client.__wrapped__()


def test_a_window_closes_after_two_quiet_hours():
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": settings.RATELIMIT_ALL_PER_SESSION + 1})
        assert limits.read_status(WHO).spent
        redis.advance(limits.WINDOW_SECONDS)
        assert not limits.read_status(WHO).spent


def test_a_late_refund_leaves_no_counter_without_expiry_or_below_zero():
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

        # Nor below zero, which would give the new window more room.
        assert all(a.used == 0 for a in limits.read_status(WHO).allowances)
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
    # 100 millionths of a dollar.
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 0.0001)
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
    # 100 millionths of a dollar.
    monkeypatch.setattr(settings, "RATELIMIT_EXPENSIVE_PER_SESSION", 0.0001)
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 101, "expensive": 101})
        redis.advance(600)
        limits.reserve(WHO, {"all": 10, "expensive": 10}, refusing=("all",))
        status = limits.read_status(WHO)

    spent = allowance(status, "expensive", "session")
    assert spent.resets_in == limits.WINDOW_SECONDS - 600
    # The allowances with room left keep their window too.
    assert {a.resets_in for a in status.allowances} == {limits.WINDOW_SECONDS - 600}


MINUTES = 60


def test_a_window_runs_two_hours_from_its_first_message_whatever_follows():
    """Each message let through used to restart the two hours, so a school
    sending all morning never got its allowance back."""
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 10, "expensive": 10})
        redis.advance(90 * MINUTES)
        limits.reserve(WHO, {"all": 10, "expensive": 10})
        status = limits.read_status(WHO)
        assert {a.resets_in for a in status.allowances} == {30 * MINUTES}

        redis.advance(30 * MINUTES)
        assert all(a.used == 0 for a in limits.read_status(WHO).allowances)


def test_a_refused_message_never_moves_a_window(monkeypatch):
    monkeypatch.setattr(settings, "RATELIMIT_ALL_PER_SESSION", 100)
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 101})
        redis.advance(90 * MINUTES)
        with pytest.raises(AllowanceSpent) as refusal:
            limits.reserve(WHO, {"all": 10})
        status = limits.read_status(WHO)

    [spent] = refusal.value.spent
    assert spent.resets_in == 30 * MINUTES
    assert {a.resets_in for a in status.allowances if a.used} == {30 * MINUTES}


def test_a_settled_turn_never_moves_a_window():
    with fake_redis(limits) as redis:
        charge = limits.Charge.reserve(
            WHO, {"a": limits.Call(10, written=500), "b": limits.Call(10)}
        )
        redis.advance(90 * MINUTES)
        charge.settle({"a": None, "b": None})
        status = limits.read_status(WHO)

    whole = allowance(status, "all", "session")
    assert (whole.used, whole.resets_in) == (20, 30 * MINUTES)


def test_a_message_after_the_reset_opens_a_new_window():
    with fake_redis(limits) as redis:
        limits.reserve(WHO, {"all": 10})
        redis.advance(limits.WINDOW_SECONDS)
        limits.reserve(WHO, {"all": 7})
        whole = allowance(limits.read_status(WHO), "all", "session")

    assert (whole.used, whole.resets_in) == (7, limits.WINDOW_SECONDS)


def test_the_cli_tells_a_counter_that_never_resets_from_none(caplog, monkeypatch):
    monkeypatch.setattr(limits, "get_app_settings", no_stored_settings)
    with fake_redis(limits) as redis, caplog.at_level("INFO", "comparia.arena"):
        redis.set(limits.budget_key("all", WHO.personal), 10)
        redis.set(limits.budget_key("expensive", WHO.personal), 12_345, ex=61)
        asyncio.run(limits_show(session="sess-a"))
    assert "s:sess-a all: 10 of 3,000,000, never resets" in caplog.text
    assert "s:sess-a expensive: $0.0123 of $0.4000, resets in 2 min" in caplog.text


def test_the_cli_refuses_a_reset_with_no_one_to_reset(caplog):
    with fake_redis(limits), pytest.raises(SystemExit) as exit:
        limits_reset()
    assert exit.value.code == 1
    assert "Give --session, --ip or both." in caplog.text


class Redis6(FakeRedis):
    """A Redis older than 7, which has neither EXPIRETIME nor EXPIRE NX."""

    def refuses(self, name, kwargs):
        if name == "expiretime":
            return ResponseError("unknown command 'expiretime'")
        if name == "expire" and kwargs.get("nx"):
            return ResponseError("wrong number of arguments for 'expire' command")
        return None


def test_an_older_redis_still_tells_when_an_allowance_lifts(monkeypatch):
    """Without EXPIRETIME, a spent allowance is read and refused all the
    same, its reset time read from PTTL and rounded up to the second."""
    monkeypatch.setattr(settings, "RATELIMIT_ALL_PER_SESSION", 100)
    monkeypatch.setattr(limits, "_expiry_command", "expiretime")
    redis = Redis6(now=1_800_000_000.5)
    monkeypatch.setattr(limits, "now", lambda: redis.now)
    with fake_redis(limits, fake=redis):
        limits.reserve(WHO, {"all": 101})
        redis.advance(600)
        status = limits.read_status(WHO)
        # The refusal learns it on its own too.
        monkeypatch.setattr(limits, "_expiry_command", "expiretime")
        with pytest.raises(AllowanceSpent) as refusal:
            limits.reserve(WHO, {"all": 1})

    lifts = 1_800_000_000 + limits.WINDOW_SECONDS + 1
    spent = allowance(status, "all", "session")
    assert (spent.resets_in, spent.expires_at) == (limits.WINDOW_SECONDS - 600, lifts)
    [refused] = refusal.value.spent
    assert refused.expires_at == lifts
    # The refund came back, and the counter kept its window.
    assert redis.get(limits.budget_key("all", WHO.personal)) == "101"
