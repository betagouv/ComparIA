"""
What a spent expensive allowance does to the arena (no network, no DB, no real
Redis).

It used to refuse every message, cheap duels included. Now new draws leave
expensive models out, a custom pick of one is refused with its id, and a
conversation already started with one finishes: refusing it would tell the
person, before the reveal, that one of the two models is expensive. Only the
whole allowance stops it.
"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import backend.arena.limits as limits
import backend.arena.router as arena_router
from backend.config import settings
from tests.arena.test_spend_budget import (
    CHEAP,
    EXPENSIVE,
    ME,
    NETWORK,
    RESERVED,
    WEIGHT,
    arena,
    counter,
    gate,
    patched,
    route_only,
    start,
)

SPENT = settings.RATELIMIT_EXPENSIVE_PER_IP + 1


def spend(redis, pool, identity):
    redis.set(limits.budget_key(pool, identity), SPENT, ex=limits.WINDOW_SECONDS)


@pytest.mark.parametrize("identity", [ME, NETWORK])
def test_a_cheap_duel_starts_with_the_expensive_allowance_spent(identity):
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        spend(state.redis, "expensive", identity)

        response = start("add_first_text", state)

        assert response.status_code == 200
        assert state.draws == [(EXPENSIVE,)]
        assert counter(state.redis, "all", ME) == 2 * RESERVED["add_first_text"]
        assert counter(state.redis, "expensive", identity) == SPENT
        # Recorded, so the ranking can set these duels apart.
        assert [c.expensive_paused for c in state.new_comparisons] == [True]


def test_a_draw_keeps_expensive_models_while_the_allowance_has_room():
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        start("add_first_text", state)

        assert state.draws == [()]
        assert [c.expensive_paused for c in state.new_comparisons] == [False]
        assert counter(state.redis, "expensive", ME) == (
            WEIGHT * RESERVED["add_first_text"]
        )


@pytest.mark.parametrize("route", ["add_text", "retry"])
def test_a_started_expensive_conversation_goes_on_while_the_whole_allowance_has_room(
    route,
):
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        spend(state.redis, "expensive", ME)
        state.redis.advance(600)

        response = start(route, state)

        assert response.status_code == 200
        # Its turns still count, and the reset time already told stays put.
        assert counter(state.redis, "expensive", ME) == (
            SPENT + WEIGHT * RESERVED[route]
        )
        assert state.redis.ttl(limits.budget_key("expensive", ME)) == (
            limits.WINDOW_SECONDS - 600
        )


@pytest.mark.parametrize("route", ["add_text", "retry"])
def test_a_started_expensive_conversation_stops_on_the_whole_allowance(route):
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        spend(state.redis, "all", ME)

        with pytest.raises(HTTPException) as refusal:
            asyncio.run(route_only(route, state))

        assert refusal.value.detail == "allowance_spent"
        assert state.provider_calls == 0


@pytest.mark.parametrize("selection", [[EXPENSIVE], [CHEAP, EXPENSIVE]])
def test_a_custom_pick_of_an_expensive_model_is_refused_with_its_id(selection, caplog):
    with arena() as state:
        spend(state.redis, "expensive", NETWORK)
        before = dict(state.redis.store)
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

        assert refusal.value.status_code == 429
        assert refusal.value.detail == "expensive_allowance_spent"
        assert refusal.value.limit.scope == "network"
        assert refusal.value.limit.llm_ids == [EXPENSIVE]
        assert refusal.value.limit.resets_in == limits.WINDOW_SECONDS
        assert {k: v for k, v in state.redis.store.items() if v} == before
        assert state.created == 0
        # The refusal leaves a trace for whoever looks into a complaint.
        assert str(EXPENSIVE) in caplog.text


def test_a_draw_that_meets_an_allowance_spent_meanwhile_draws_again():
    """Two first messages read "available" at once and the first one spends
    the allowance. The second is still refused when it charges, then draws
    again without expensive models."""
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        spend(state.redis, "expensive", ME)
        stale = SimpleNamespace(expensive_available=True)
        with patched(arena_router, read_status=lambda _who: stale):
            response = asyncio.run(route_only("add_first_text", state))

        assert response.status_code == 200
        assert state.draws == [(), (EXPENSIVE,)]
        assert [c.expensive_paused for c in state.new_comparisons] == [True]
        assert counter(state.redis, "all", ME) == 2 * RESERVED["add_first_text"]
        assert counter(state.redis, "expensive", ME) == SPENT


def test_a_draw_that_meets_both_allowances_spent_meanwhile_is_told_the_whole():
    """The expensive allowance lifting later must not turn the refusal into
    one that says to pick other models."""
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        spend(state.redis, "expensive", ME)
        state.redis.set(limits.budget_key("all", ME), SPENT, ex=60)
        stale = SimpleNamespace(expensive_available=True)
        with (
            patched(arena_router, read_status=lambda _who: stale),
            pytest.raises(HTTPException) as refusal,
        ):
            asyncio.run(route_only("add_first_text", state))

        assert refusal.value.detail == "allowance_spent"
        assert refusal.value.limit.resets_in == 60
        assert state.created == 0


def test_a_custom_pick_that_meets_an_allowance_spent_meanwhile_is_refused():
    with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
        spend(state.redis, "expensive", ME)
        stale = SimpleNamespace(expensive_available=True)
        with (
            patched(arena_router, read_status=lambda _who: stale),
            pytest.raises(HTTPException) as refusal,
        ):
            asyncio.run(
                route_only(
                    "add_first_text",
                    state,
                    mode="custom",
                    custom_models_selection=[str(EXPENSIVE)],
                )
            )

        assert refusal.value.detail == "expensive_allowance_spent"
        assert refusal.value.limit.llm_ids == [EXPENSIVE]
