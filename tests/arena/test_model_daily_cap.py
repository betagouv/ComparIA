"""
A daily cap per model across everyone (no network, no DB, no real Redis).

Each model's spend is counted per Paris calendar day, in estimated dollars,
reserved before the call and settled once the turn is over, like the
allowances. Once a capped model's day is full it rests until midnight in
Paris: new draws leave it out for everyone, a custom pick of it is refused,
and the conversations already under way with it finish.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

import backend.arena.limits as limits
import backend.arena.router as arena_router
from backend.arena.limits import Allowance, Call, Charge, Day, Identity
from backend.llms.data import NoModelLeft
from tests.arena.fakes import FakeRedis, fake_redis
from tests.arena.test_spend_budget import (
    ANSWER,
    CHEAP,
    EXPENSIVE,
    ME,
    NETWORK,
    SENT,
    arena,
    gate,
    patched,
    read,
    route_only,
    start,
    usd,
)

PARIS = ZoneInfo("Europe/Paris")
# 23:50 in Paris on a summer day, 21:50 UTC.
LATE = datetime(2026, 7, 1, 23, 50, tzinfo=PARIS).timestamp()
WHO = Identity(ME, NETWORK)


def paris(moment):
    return datetime.fromtimestamp(moment, PARIS)


def day_of(redis, llm_id):
    return redis.hgetall(limits.model_day_key(llm_id, Day.at()))


def spent(redis, llm_id):
    return int(day_of(redis, llm_id).get("usd", 0))


def answer(text, cached=False):
    return SimpleNamespace(content=text, reasoning_content=None, is_cached=cached)


@pytest.fixture
def clock(monkeypatch):
    """The daily caps' clock, on the fake Redis's."""
    redis = FakeRedis(now=LATE)
    monkeypatch.setattr(limits, "now", lambda: redis.now)
    with fake_redis(limits, fake=redis):
        yield redis


def test_a_day_ends_at_midnight_in_paris():
    day = Day.at(LATE)

    assert day.name == "20260701"
    assert paris(day.ends_at) == datetime(2026, 7, 2, tzinfo=PARIS)
    assert day.ends == datetime(2026, 7, 1, 22, tzinfo=timezone.utc)
    # 00:10 in Paris is still the day before in UTC.
    assert Day.at(LATE + 20 * 60).name == "20260702"


def test_a_day_that_changes_the_clocks_still_ends_at_midnight():
    # The night of 24 to 25 October 2026 lasts 25 hours in Paris.
    day = Day.at(datetime(2026, 10, 24, 12, tzinfo=PARIS).timestamp())

    assert paris(day.ends_at) == datetime(2026, 10, 25, tzinfo=PARIS)
    assert Day.at(day.ends_at).ends_at - day.ends_at == 25 * 3600


def test_a_turn_counts_what_each_model_costs_on_its_day(clock):
    llm = SimpleNamespace(id=EXPENSIVE, price_in=4.0, price_out=12.0)
    charge = Charge.reserve(WHO, {"a": Call.of(llm, 100, written=50)})

    assert day_of(clock, EXPENSIVE) == {"usd": "250", "in": "100", "out": "50"}

    charge.settle({"a": answer("x" * 200)})

    assert day_of(clock, EXPENSIVE) == {
        "usd": str(usd(100, 200)),
        "in": "100",
        "out": "200",
        "answers": "1",
    }
    assert clock.ttl(limits.model_day_key(EXPENSIVE, Day.at())) == 10 * 60


def test_a_cached_answer_costs_its_model_nothing(clock):
    llm = SimpleNamespace(id=EXPENSIVE, price_in=4.0, price_out=12.0)
    charge = Charge.reserve(WHO, {"a": Call.of(llm, 100, written=50)})

    charge.settle({"a": answer("x" * 200, cached=True)})

    # The reservation came back; the answer is still counted, as cached.
    assert day_of(clock, EXPENSIVE) == {
        "usd": "0",
        "in": "0",
        "out": "0",
        "answers": "1",
        "cached": "1",
    }


def test_a_turn_settled_after_midnight_leaves_no_day_behind(clock):
    llm = SimpleNamespace(id=EXPENSIVE, price_in=4.0, price_out=12.0)
    charge = Charge.reserve(WHO, {"a": Call.of(llm, 100, written=5000)})
    yesterday = limits.model_day_key(EXPENSIVE, Day.at())
    clock.advance(20 * 60)

    charge.settle({"a": answer("x" * 10)})

    # The refund would have started the old day below zero, with no end.
    assert clock.ttl(yesterday) == -2
    assert day_of(clock, EXPENSIVE) == {}


def test_counting_a_day_never_stops_a_turn_when_redis_fails(clock):
    llm = SimpleNamespace(id=EXPENSIVE, price_in=4.0, price_out=12.0)
    # The allowances' pipeline works, the day's after it does not.
    clock.pipelines_left = 1

    charge = Charge.reserve(WHO, {"a": Call.of(llm, 100)})
    charge.settle({"a": answer("x")})


def capped(llm_id, cap):
    return SimpleNamespace(id=llm_id, daily_usd_cap=cap)


def fill(redis, llm_id, micro_usd):
    limits.count_day(Day.at(), {llm_id: {"usd": micro_usd}})


def test_a_model_rests_once_its_day_reaches_the_cap(clock):
    fill(clock, EXPENSIVE, 999_999)
    models = [capped(EXPENSIVE, 1.0), capped(CHEAP, None)]

    assert limits.resting_models(models) == {}

    fill(clock, EXPENSIVE, 1)

    assert limits.resting_models(models) == {EXPENSIVE: Day.at().ends}


def test_a_cap_of_zero_keeps_a_model_out_all_day(clock):
    assert limits.resting_models([capped(EXPENSIVE, 0)]) == {EXPENSIVE: Day.at().ends}


def test_a_model_comes_back_at_midnight_in_paris(clock):
    fill(clock, EXPENSIVE, 5_000_000)
    models = [capped(EXPENSIVE, 1.0)]
    assert EXPENSIVE in limits.resting_models(models)

    clock.advance(9 * 60)
    assert EXPENSIVE in limits.resting_models(models)

    clock.advance(2 * 60)
    assert limits.resting_models(models) == {}


def test_no_cap_reads_nothing():
    redis = FakeRedis(pipelines_that_work=0)
    with fake_redis(limits, fake=redis):
        assert limits.resting_models([capped(EXPENSIVE, None)]) == {}


# Through the routes, with the arena stubs of test_spend_budget.


def full_day(state, llm_id=EXPENSIVE):
    fill(state.redis, llm_id, 10_000_000)


def test_a_full_model_is_left_out_of_new_draws():
    with arena(llm_ids=(CHEAP, EXPENSIVE), caps={EXPENSIVE: 1.0}) as state:
        with patched(limits, now=lambda: state.redis.now):
            full_day(state)

            response = start("add_first_text", state)

        assert response.status_code == 200
        assert state.draws == [(EXPENSIVE,)]
        # Not the person's allowance: nothing records the draw as paused.
        assert [c.expensive_paused for c in state.new_comparisons] == [False]


def test_the_turn_that_fills_a_day_rests_the_model_for_the_next_draw():
    cost = usd(SENT["add_first_text"], len(ANSWER))
    with arena(llm_ids=(CHEAP, EXPENSIVE), caps={EXPENSIVE: cost / 1e6}) as state:
        with patched(limits, now=lambda: state.redis.now):
            read(start("add_first_text", state))
            assert spent(state.redis, EXPENSIVE) == cost

            start("add_first_text", state)

        assert state.draws == [(), (EXPENSIVE,)]


@pytest.mark.parametrize("selection", [[EXPENSIVE], [CHEAP, EXPENSIVE]])
def test_a_custom_pick_of_a_full_model_is_refused_until_midnight(selection):
    with arena(caps={EXPENSIVE: 1.0}) as state:
        with patched(limits, now=lambda: state.redis.now):
            full_day(state)
            gate("add_first_text")

            with pytest.raises(HTTPException) as refusal:
                asyncio.run(
                    route_only(
                        "add_first_text",
                        state,
                        mode="custom",
                        custom_models_selection=[str(llm_id) for llm_id in selection],
                    )
                )
            midnight = Day.at()

        assert refusal.value.status_code == 429
        assert refusal.value.detail == "model_full_today"
        assert refusal.value.limit.scope is None
        assert refusal.value.limit.llm_ids == [EXPENSIVE]
        assert refusal.value.limit.resets_at == midnight.ends
        assert refusal.value.limit.resets_in == midnight.ends_at - int(state.redis.now)
        assert state.created == 0


def test_a_pick_both_full_and_paused_is_told_the_later_end():
    """The person's expensive allowance lifts within two hours, the cap at
    midnight: they can send the pick once both have lifted."""
    with arena(caps={EXPENSIVE: 1.0}) as state:
        with patched(limits, now=lambda: state.redis.now):
            full_day(state)
            state.redis.set(
                limits.budget_key("expensive", ME),
                limits.limit("expensive", "session") + 1,
                ex=600,
            )

            with pytest.raises(HTTPException) as refusal:
                asyncio.run(
                    route_only(
                        "add_first_text",
                        state,
                        mode="custom",
                        custom_models_selection=[str(EXPENSIVE)],
                    )
                )
            midnight = Day.at().ends

        assert state.redis.now + 600 < midnight.timestamp()
        assert refusal.value.detail == "model_full_today"
        assert refusal.value.limit.resets_at == midnight


@pytest.mark.parametrize("route", ["add_text", "retry"])
def test_a_conversation_under_way_with_a_full_model_goes_on(route):
    """Refusing it would tell the person, before the reveal, which model is
    in the pair. Its turns still count on the model's day."""
    with arena(llm_ids=(CHEAP, EXPENSIVE), caps={EXPENSIVE: 1.0}) as state:
        with patched(limits, now=lambda: state.redis.now):
            full_day(state)

            read(start(route, state))

            assert spent(state.redis, EXPENSIVE) == 10_000_000 + usd(
                SENT[route], len(ANSWER)
            )
        assert state.provider_calls == 1


def test_every_model_is_counted_capped_or_not():
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        with patched(limits, now=lambda: state.redis.now):
            read(start("add_first_text", state))

            assert spent(state.redis, EXPENSIVE) == usd(
                SENT["add_first_text"], len(ANSWER)
            )
            assert spent(state.redis, CHEAP) > 0
            assert day_of(state.redis, CHEAP)["answers"] == "1"


def test_a_mode_left_with_only_full_models_is_refused_with_no_model_named():
    midnight = Day.at().ends

    refusal = arena_router.pick_refusal(NoModelLeft(), {EXPENSIVE: midnight}, ())

    assert refusal.detail == "model_full_today"
    assert refusal.limit.llm_ids == []
    assert refusal.limit.resets_at == midnight


@pytest.mark.parametrize(
    ("resets_in", "detail"),
    [(600, "model_full_today"), (2 * 3600, "expensive_allowance_spent")],
)
def test_a_pick_of_a_full_model_and_a_paused_one_is_told_the_later_end(
    resets_in, detail
):
    """The full model comes back in an hour, the paused one once the
    allowance lifts."""
    paused = uuid4()
    back = datetime.now(timezone.utc) + timedelta(hours=1)
    spent = [Allowance("expensive", "session", ME, 2, 1, resets_in)]

    refusal = arena_router.pick_refusal(
        NoModelLeft([EXPENSIVE, paused]), {EXPENSIVE: back}, spent
    )

    assert refusal.detail == detail
    assert refusal.limit.llm_ids == [EXPENSIVE, paused]


def test_unknown_model_ids_are_not_counted(clock):
    charge = Charge.reserve(WHO, {"a": Call(100, 50, 1.0, 1.0)})
    charge.settle({"a": answer("x")})

    assert not [key for key in clock.store if "model_day" in key]


def test_two_models_of_a_turn_each_get_their_own_day(clock):
    pricey = SimpleNamespace(id=EXPENSIVE, price_in=4.0, price_out=12.0)
    cheap = SimpleNamespace(id=CHEAP, price_in=0.4, price_out=1.2)

    Charge.reserve(WHO, {"a": Call.of(pricey, 100), "b": Call.of(cheap, 100)}).settle(
        {"a": answer("x" * 10), "b": None}
    )

    assert day_of(clock, EXPENSIVE) == {
        "usd": str(usd(100, 10)),
        "in": "100",
        "out": "10",
        "answers": "1",
    }
    # Sent 100 characters at 0.40 per million tokens, and no answer.
    assert day_of(clock, CHEAP) == {"usd": "10", "in": "100"}
