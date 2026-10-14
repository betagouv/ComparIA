"""
How many turns one network may have the models answer at once (no network,
no DB, no real Redis).

A burst of hundreds of messages sent together used to pass the allowances
before any long answer was counted. Each turn now holds a slot of its network
until its answer is sent or it fails; past the cap, a turn is refused with a
429 to try again in a few seconds, whatever the models.
"""

import os

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from fastapi import Depends, FastAPI, HTTPException  # noqa: E402
from fastapi.responses import StreamingResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import backend.arena.in_flight as in_flight  # noqa: E402
import backend.arena.limits as limits  # noqa: E402
import backend.arena.router as arena_router  # noqa: E402
from backend.arena.in_flight import TooManyAtOnce, TurnSlot  # noqa: E402
from backend.config import settings  # noqa: E402
from tests.arena.fakes import FakeRedis, fake_redis  # noqa: E402

NETWORK = "ip:testclient"
CAP = 3


@pytest.fixture
def redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(in_flight, "now", lambda: fake.now)
    monkeypatch.setattr(limits, "_stored", {})
    monkeypatch.setattr(settings, "RATELIMIT_IN_FLIGHT_PER_NETWORK", CAP)
    with fake_redis(in_flight, fake=fake):
        yield fake


def held(redis, network=NETWORK):
    key = in_flight.REDIS_IN_FLIGHT_KEY.format(network=network.split(":", 1)[1])
    return redis.zcard(key)


@pytest.fixture
def app(redis):
    """A route holding a slot the way the arena's do. `seen` holds how many
    slots the network held while the answer streamed."""
    app = FastAPI()
    app.state.seen = []

    @app.post("/turn", dependencies=[Depends(in_flight.hold_turn_slot)])
    async def turn(fail: str = "") -> StreamingResponse:
        if fail == "before":
            raise HTTPException(status_code=422, detail="spam_detected")

        async def answer():
            app.state.seen.append(held(redis))
            yield "data: chunk\n\n"
            if fail == "during":
                raise RuntimeError("the model went away")
            yield "data: complete\n\n"

        return StreamingResponse(answer(), media_type="text/event-stream")

    return app


def test_a_turn_holds_a_slot_until_its_answer_is_sent(app, redis):
    response = TestClient(app).post("/turn")

    assert response.status_code == 200
    assert app.state.seen == [1]
    assert held(redis) == 0


def test_a_turn_refused_before_it_starts_gives_its_slot_back(app, redis):
    response = TestClient(app).post("/turn", params={"fail": "before"})

    assert response.status_code == 422
    assert held(redis) == 0


def test_a_turn_that_fails_while_answering_gives_its_slot_back(app, redis):
    with pytest.raises(RuntimeError):
        TestClient(app).post("/turn", params={"fail": "during"})

    assert held(redis) == 0


def test_past_the_cap_a_turn_is_told_to_try_again_in_a_few_seconds(app, redis):
    for _ in range(CAP):
        TurnSlot.take(NETWORK)

    response = TestClient(app).post("/turn")

    assert response.status_code == 429
    assert response.json() == {"detail": "too_many_at_once"}
    assert response.headers["Retry-After"] == "5"
    # The refused turn took nothing.
    assert held(redis) == CAP
    assert app.state.seen == []


def test_another_network_is_not_held_back(app, redis):
    for _ in range(CAP):
        TurnSlot.take("ip:10.0.0.9")

    assert TestClient(app).post("/turn").status_code == 200


def test_a_slot_never_given_back_lapses(redis):
    for _ in range(CAP):
        TurnSlot.take(NETWORK)
    with pytest.raises(TooManyAtOnce):
        TurnSlot.take(NETWORK)

    redis.advance(in_flight.SLOT_SECONDS + 1)

    TurnSlot.take(NETWORK)
    assert held(redis) == 1


def test_turns_sent_together_pass_up_to_the_cap(redis):
    taken, refused = [], 0
    for _ in range(CAP + 5):
        try:
            taken.append(TurnSlot.take(NETWORK))
        except TooManyAtOnce:
            refused += 1

    assert (len(taken), refused) == (CAP, 5)
    taken[0].release()
    TurnSlot.take(NETWORK)


def test_a_slot_given_back_twice_frees_one(redis):
    first = TurnSlot.take(NETWORK)
    TurnSlot.take(NETWORK)

    first.release()
    first.release()

    assert held(redis) == 1


def test_the_cap_is_an_admin_setting(redis, monkeypatch):
    monkeypatch.setattr(limits, "_stored", {"in_flight_per_network": 1})
    TurnSlot.take(NETWORK)

    with pytest.raises(TooManyAtOnce):
        TurnSlot.take(NETWORK)


def test_a_turn_goes_on_when_redis_is_down(app, redis):
    redis.pipelines_left = 0

    assert TestClient(app).post("/turn").status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/arena/add_first_text",
        "/arena/add_text/{comparison_id}",
        "/arena/retry/{comparison_id}",
    ],
)
def test_every_route_that_calls_the_models_holds_a_slot(path):
    (route,) = [r for r in arena_router.router.routes if r.path == path]

    assert in_flight.hold_turn_slot in [d.dependency for d in route.dependencies]
