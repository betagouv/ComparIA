"""
A session that keeps starting comparisons without voting gets harder captchas,
until it votes again (no DB, Redis replaced by a dict).

Run with pytest, or directly:
    uv run python tests/arena/test_unvoted_captcha.py
"""

import asyncio
import base64
import contextlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

from fastapi import HTTPException  # noqa: E402
from starlette.requests import Request  # noqa: E402

import backend.arena.router as arena_router  # noqa: E402
import backend.arena.session as session  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from backend.arena.captcha import generate_challenge, solved_max_number  # noqa: E402
from backend.config import (  # noqa: E402
    ALTCHA_HARD_MAX_NUMBER,
    ALTCHA_MAX_NUMBER,
    ALTCHA_UNVOTED_COMPARISONS,
)
from utils.database.models.turn import TurnVoteAnnotate, TurnVoteChoice  # noqa: E402

SESSION = "s" * 64


class FakeRedis:
    def __init__(self):
        self.store: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        pass

    def get(self, key):
        value = self.store.get(key)
        return None if value is None else str(value)

    def delete(self, key):
        self.store.pop(key, None)


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
def started(comparisons: int):
    """A session that started `comparisons` comparisons without voting."""
    fake = FakeRedis()
    with patched(session, get_redis_client=lambda: fake):
        for _ in range(comparisons):
            session.increment_unvoted(SESSION)
        yield


def token(max_number: int) -> str:
    challenge = generate_challenge(max_number)
    payload = {
        "algorithm": challenge["algorithm"],
        "challenge": challenge["challenge"],
        "number": 0,
        "salt": challenge["salt"],
        "signature": challenge["signature"],
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()


def challenge_size() -> int:
    return asyncio.run(arena_router.get_challenge(SESSION))["maxNumber"]


def accepted(max_number: int) -> bool:
    try:
        arena_router.assert_captcha_paid(token(max_number), SESSION)
    except HTTPException as error:
        assert error.detail[0]["msg"] == "captcha_failed"
        return False
    return True


def vote(choice: bool):
    turn = SimpleNamespace(id=uuid4(), llm_msg_a=object(), llm_msg_b=object())
    turn.choice = None if choice else "a_better"
    comparison = SimpleNamespace(id=uuid4(), turns=[turn], error=None)
    body = (
        TurnVoteChoice(turn_id=turn.id, choice="a_better")
        if choice
        else TurnVoteAnnotate(
            turn_id=turn.id, pos="a", keyword_annotations=[], custom_annotation=None
        )
    )
    request = Request({"type": "http", "headers": [], "client": ("10.0.0.1", 1)})

    async def nothing(*_args, **_kwargs):
        return None

    with patched(arena_router, update_turn_vote=nothing, check_vote_tags=nothing):
        asyncio.run(arena_router.vote(comparison, body, SESSION, request))


def test_a_session_that_votes_gets_ordinary_challenges():
    with started(ALTCHA_UNVOTED_COMPARISONS - 1):
        assert challenge_size() == ALTCHA_MAX_NUMBER
        assert accepted(ALTCHA_MAX_NUMBER)


def test_a_session_that_never_votes_gets_hard_challenges():
    with started(ALTCHA_UNVOTED_COMPARISONS):
        assert challenge_size() == ALTCHA_HARD_MAX_NUMBER


def test_an_easy_challenge_fetched_just_before_the_line_still_passes():
    """The browser fetches its next challenge while the comparison that
    crosses the line is being created."""
    with started(ALTCHA_UNVOTED_COMPARISONS):
        assert accepted(ALTCHA_MAX_NUMBER)


def test_past_the_line_an_easy_challenge_is_refused():
    with started(ALTCHA_UNVOTED_COMPARISONS + 1):
        assert not accepted(ALTCHA_MAX_NUMBER)
        assert accepted(ALTCHA_HARD_MAX_NUMBER)


def test_a_token_from_before_this_change_counts_as_easy():
    old = base64.b64encode(json.dumps({"salt": "abc?expires=1"}).encode()).decode()
    assert solved_max_number(old) == 0
    assert solved_max_number("not base64 json") == 0


def test_voting_brings_back_ordinary_challenges():
    with started(ALTCHA_UNVOTED_COMPARISONS + 3):
        vote(choice=True)
        assert challenge_size() == ALTCHA_MAX_NUMBER
        assert accepted(ALTCHA_MAX_NUMBER)


def test_annotating_is_not_a_vote():
    with started(ALTCHA_UNVOTED_COMPARISONS + 3):
        vote(choice=False)
        assert challenge_size() == ALTCHA_HARD_MAX_NUMBER


def test_a_redis_outage_asks_for_nothing_harder():
    class BrokenRedis:
        def __getattr__(self, _name):
            raise ConnectionError("Redis is down")

    with patched(session, get_redis_client=BrokenRedis):
        session.increment_unvoted(SESSION)
        assert challenge_size() == ALTCHA_MAX_NUMBER
        assert accepted(ALTCHA_MAX_NUMBER)


if __name__ == "__main__":
    test_a_session_that_votes_gets_ordinary_challenges()
    test_a_session_that_never_votes_gets_hard_challenges()
    test_an_easy_challenge_fetched_just_before_the_line_still_passes()
    test_past_the_line_an_easy_challenge_is_refused()
    test_a_token_from_before_this_change_counts_as_easy()
    test_voting_brings_back_ordinary_challenges()
    test_annotating_is_not_a_vote()
    test_a_redis_outage_asks_for_nothing_harder()
    print("Unvoted captcha cases passed.")
