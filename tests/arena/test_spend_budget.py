"""
When the arena charges a message against the character budgets (no network, no
DB, no real Redis).

The budgets used to be charged once both answers had streamed in full and
without error. A visitor who closed the connection halfway, or sent many
requests at once, got the models' answers and was never charged. Every route
that calls the models now pays for what they are sent before it starts them,
and for what they wrote once the turn is over, however it ended.

Run with pytest, or directly:
    uv run python tests/arena/test_spend_budget.py
"""

import asyncio
import contextlib
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from uuid import UUID  # noqa: E402

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from starlette.requests import Request  # noqa: E402

import backend.arena.limits as limits  # noqa: E402
import backend.arena.models as arena_models  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
import backend.arena.session as session  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.config import ANONYMOUS_SESSION_COOKIE, settings  # noqa: E402
from backend.llms.data import NoModelLeft  # noqa: E402
from tests.arena.fakes import FakeRedis  # noqa: E402
from utils.database.models import LLMMessageCreate, UserMessageRead  # noqa: E402

SESSION = "b" * 64
IP = "10.0.0.1"
PROMPT = "Bonjour, explique la photosynthese"
CHEAP, EXPENSIVE = uuid4(), uuid4()
WEIGHT = 4
ME, NETWORK = f"s:{SESSION}", f"ip:{IP}"
# What each model writes, all at once.
ANSWER = "La photosynthese transforme la lumiere en sucres. " * 4

# What each side is sent: the prompt, and for a follow-up the turn before it
# too. Nothing else, since the models here have no system prompt.
SENT = {
    "add_first_text": len(PROMPT),
    "add_text": 2 * len(PROMPT),
    "retry": len(PROMPT),
}
# What each side is charged before the models start: what it is sent and a
# typical answer, settled to the real one when the turn ends.
RESERVED = {
    route: sent + settings.RATELIMIT_EXPECTED_ANSWER_CHARS
    for route, sent in SENT.items()
}


def counter(redis, pool, identity):
    return int(redis.get(limits.budget_key(pool, identity)) or 0)


def make_request(path):
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": path,
            "path_params": {},
            "query_string": b"",
            "headers": [],
            "client": (IP, 1234),
        }
    )


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


@contextlib.contextmanager
def arena(llm_ids=(CHEAP, CHEAP)):
    """The arena routes against stubs. `provider_calls` counts every time the
    models are started; `created` every comparison, turn or prompt check
    written; `draws` the models each draw had to leave out; `new_comparisons`
    what each first message asked to save. Set `in_step` to a
    barrier to hold each request just before it charges until the others get
    there too."""
    redis = FakeRedis()
    state = SimpleNamespace(
        redis=redis,
        provider_calls=0,
        created=0,
        in_step=None,
        draws=[],
        new_comparisons=[],
    )
    llm_a, llm_b = llm_ids

    def comparison(error=None):
        turn = SimpleNamespace(
            id=uuid4(),
            user_msg=UserMessageRead(content=PROMPT),
            llm_msg_a=None,
            llm_msg_b=None,
        )
        return SimpleNamespace(
            id=uuid4(),
            turns=[turn],
            error=error,
            mode="random",
            llm_id_a=llm_a,
            llm_id_b=llm_b,
            system_msg_a=None,
            system_msg_b=None,
        )

    state.comparison = comparison

    def pick_two(_mode, selection, hard_excluded=()):
        state.draws.append(tuple(hard_excluded))
        if refused := [
            UUID(llm_id) for llm_id in selection or [] if UUID(llm_id) in hard_excluded
        ]:
            raise NoModelLeft(refused)
        # With models left out, the draw falls on two cheap ones.
        return (CHEAP, CHEAP) if hard_excluded else (llm_a, llm_b)

    async def get_llms_data():
        if state.in_step:
            await state.in_step.wait()
        return SimpleNamespace(
            pick_two=pick_two,
            expensive_models=[EXPENSIVE],
            weight=lambda llm_id: WEIGHT if llm_id == EXPENSIVE else 1,
            all={llm_id: SimpleNamespace(system_prompt=None) for llm_id in llm_ids},
        )

    async def run_checks(_text, _field, _request, _warning_token, **_kwargs):
        return SimpleNamespace(pending_warning=False)

    async def save_prompt_check_result(check):
        state.created += 1
        return check

    async def terms_version(**_kwargs):
        return "2026.07"

    async def create_comparison(new_comparison):
        state.created += 1
        state.new_comparisons.append(new_comparison)
        return comparison()

    async def add_comparison_turn(comparison_id, _text, *_args, **_kwargs):
        state.created += 1
        current = comparison()
        return current, current.turns[-1]

    async def noop(*_args, **_kwargs):
        return None

    async def stream_comparison_messages(_comparison, turn, *_args, **_kwargs):
        state.provider_calls += 1
        for pos in ("a", "b"):
            setattr(turn, f"llm_msg_{pos}", LLMMessageCreate(content=ANSWER))
            yield {"type": "chunk", "pos": pos}
        yield {"type": "complete"}

    with (
        patched(limits, get_redis_client=lambda: redis),
        patched(session, get_redis_client=lambda: redis),
    ):
        with patched(arena_models, verify_altcha_token=lambda _token: (True, None)):
            with patched(
                arena_router,
                get_llms_data=get_llms_data,
                run_checks=run_checks,
                save_prompt_check_result=save_prompt_check_result,
                get_current_terms_acceptance_version=terms_version,
                create_comparison=create_comparison,
                add_comparison_turn=add_comparison_turn,
                update_turn=noop,
                update_comparison_error=noop,
                store_comparison_metadata=lambda *_args, **_kwargs: None,
                stream_comparison_messages=stream_comparison_messages,
                format_sse_event=lambda event: f"data: {event['type']}\n\n",
                ComparisonPublic=SimpleNamespace(model_validate=lambda *_a, **_k: {}),
                TurnPublic=SimpleNamespace(model_validate=lambda *_a, **_k: {}),
            ):
                yield state


def gate(route):
    """The budget check FastAPI runs before the route."""
    arena_router.assert_allowance_left(SESSION, make_request(f"/arena/{route}"))


async def route_only(route, state, **first_text):
    """The route on its own, which hands back the stream without reading it."""
    request = make_request(f"/arena/{route}")
    if route == "add_first_text":
        body = arena_models.AddFirstTextBody(
            prompt_value=PROMPT, cohorts="", altcha_token="valid", **first_text
        )
        allowance = arena_router.read_status(limits.Identity.of(SESSION, IP))
        return await arena_router.add_first_text(
            body, None, SESSION, request, allowance
        )
    if route == "add_text":
        message = arena_models.AddTextBody(message=PROMPT, altcha_token="valid")
        return await arena_router.add_text(
            state.comparison(), message, SESSION, request
        )
    return await arena_router.retry(
        state.comparison(),
        arena_models.RetryBody(altcha_token="valid"),
        SESSION,
        request,
    )


def start(route, state):
    """What FastAPI does up to the first byte of the answer."""
    gate(route)
    return asyncio.run(route_only(route, state))


def read(response, hang_up=False):
    """Read the stream, or hang up after the first piece of an answer, as a
    client that closes the connection does."""

    async def consume():
        iterator = response.body_iterator
        async for event in iterator:
            if hang_up and "chunk" in event:
                await iterator.aclose()
                break

    asyncio.run(consume())


ROUTES = ("add_first_text", "add_text", "retry")


def each_route(test):
    def run_all():
        for route in ROUTES:
            with arena() as state:
                test(route, state)

    run_all.__name__ = test.__name__
    run_all.__doc__ = test.__doc__
    return run_all


@each_route
def test_a_message_is_charged_before_the_models_start(route, state):
    response = start(route, state)

    assert state.provider_calls == 0
    assert counter(state.redis, "all", ME) == 2 * RESERVED[route], route
    assert counter(state.redis, "all", NETWORK) == 2 * RESERVED[route], route
    assert response.status_code == 200


@each_route
def test_a_client_that_hangs_up_has_still_paid(route, state):
    """What was written before the client left counts too: the provider
    billed it."""
    read(start(route, state), hang_up=True)

    assert state.provider_calls == 1, route
    paid = 2 * SENT[route] + len(ANSWER)
    assert counter(state.redis, "all", ME) == paid, route
    assert counter(state.redis, "all", NETWORK) == paid, route


@each_route
def test_a_full_answer_is_charged_once(route, state):
    read(start(route, state))

    assert state.provider_calls == 1, route
    assert counter(state.redis, "all", ME) == 2 * (SENT[route] + len(ANSWER)), route


@each_route
def test_requests_sent_together_cannot_all_spend_the_last_of_the_budget(route, state):
    """The gate used to read the counters and the charge came later, so every
    request sent at once passed the gate before any of them was counted. Here
    both requests are past the gate and inside the route before either one
    charges."""
    state.redis.store[limits.budget_key("all", ME)] = (
        settings.RATELIMIT_ALL_PER_SESSION - 1
    )

    async def together():
        state.in_step = asyncio.Barrier(2)

        async def send():
            gate(route)
            return await route_only(route, state)

        return await asyncio.gather(send(), send(), return_exceptions=True)

    results = asyncio.run(together())
    state.in_step = None

    refused = [r for r in results if isinstance(r, HTTPException)]
    assert len(refused) == 1, f"{route}: two requests spent one budget"
    assert refused[0].status_code == 429
    assert refused[0].detail == "allowance_spent"
    assert refused[0].limit.scope == "session"

    [first] = [r for r in results if not isinstance(r, HTTPException)]
    read(first)
    assert state.provider_calls == 1, route


@each_route
def test_a_refused_message_spends_nothing_and_writes_nothing(route, state):
    """Refused, the message never reached a model. Left counted, it would keep
    eating the budgets that were not spent yet, such as the IP one a whole
    school can share."""
    spent = limits.budget_key("all", NETWORK)
    state.redis.store[spent] = settings.RATELIMIT_ALL_PER_IP + 1
    before = dict(state.redis.store)

    try:
        asyncio.run(route_only(route, state))
    except HTTPException as error:
        assert error.status_code == 429
    else:
        raise AssertionError(f"{route}: an over-budget message went through")

    assert {k: v for k, v in state.redis.store.items() if v} == before, route
    assert state.created == 0, route
    assert state.provider_calls == 0, route
    # A counter the refused message created holds nothing and must not stay in
    # Redis for ever.
    assert all(state.redis.ttl(k) > 0 for k in state.redis.store if k != spent), route


def test_an_expensive_model_spends_the_expensive_allowance_up_front():
    """Its side only, each character as many times as its weight."""
    for route in ROUTES:
        with arena(llm_ids=(CHEAP, EXPENSIVE)) as state:
            start(route, state)
            weighted = WEIGHT * RESERVED[route]
            assert counter(state.redis, "expensive", ME) == weighted, route
            assert counter(state.redis, "expensive", NETWORK) == weighted, route

        with arena(llm_ids=(CHEAP, CHEAP)) as state:
            start(route, state)
            assert counter(state.redis, "expensive", ME) == 0, route


@each_route
def test_only_the_whole_allowance_stops_a_message_at_the_gate(route, state):
    """A spent expensive allowance used to stop every message, cheap pairs
    included. It now only keeps expensive models out of new comparisons."""
    for identity, scope in ((ME, "session"), (NETWORK, "network")):
        state.redis.store = {
            limits.budget_key("all", identity): settings.RATELIMIT_ALL_PER_IP + 1
        }
        try:
            gate(route)
        except HTTPException as error:
            assert error.status_code == 429
            assert (error.detail, error.limit.scope) == ("allowance_spent", scope)
        else:
            raise AssertionError(f"{route}: a spent allowance let a message by")

    for identity in (ME, NETWORK):
        state.redis.store = {
            limits.budget_key("expensive", identity): settings.RATELIMIT_ALL_PER_IP + 1
        }
        gate(route)


@contextlib.contextmanager
def retry_client(captcha_ok=True):
    with arena() as state:
        app = FastAPI()
        app.include_router(arena_router.router)
        app.dependency_overrides[arena_router.get_comparison] = state.comparison
        with patched(
            arena_models, verify_altcha_token=lambda _token: (captcha_ok, None)
        ):
            client = TestClient(app)
            client.cookies.set(ANONYMOUS_SESSION_COOKIE, "anonymous-test-token")
            yield client, state


def test_a_retry_needs_a_solved_captcha():
    """A retry calls both models again, and it used to take no proof of work at
    all, so it was the cheap way to run them in a loop."""
    with retry_client() as (client, state):
        assert client.post(f"/arena/retry/{uuid4()}", json={}).status_code == 422
        assert client.post(f"/arena/retry/{uuid4()}").status_code == 422
        assert state.provider_calls == 0

    with retry_client(captcha_ok=False) as (client, state):
        response = client.post(f"/arena/retry/{uuid4()}", json={"altcha_token": "x"})
        assert response.status_code == 422
        assert "captcha_failed" in response.text
        assert state.provider_calls == 0


def test_a_retry_with_a_solved_captcha_goes_through_and_pays():
    with retry_client() as (client, state):
        response = client.post(f"/arena/retry/{uuid4()}", json={"altcha_token": "ok"})
        assert response.status_code == 200
        assert state.provider_calls == 1
        assert counter(state.redis, "all", "ip:testclient") == 2 * (
            SENT["retry"] + len(ANSWER)
        )


if __name__ == "__main__":
    test_a_message_is_charged_before_the_models_start()
    test_a_client_that_hangs_up_has_still_paid()
    test_a_full_answer_is_charged_once()
    test_requests_sent_together_cannot_all_spend_the_last_of_the_budget()
    test_a_refused_message_spends_nothing_and_writes_nothing()
    test_an_expensive_model_spends_the_expensive_allowance_up_front()
    test_only_the_whole_allowance_stops_a_message_at_the_gate()
    test_a_retry_needs_a_solved_captcha()
    test_a_retry_with_a_solved_captcha_goes_through_and_pays()
    print("Spend budget cases passed.")
