"""
A turn costs what the models are sent and what they write (no network, no DB,
no real Redis).

A message used to cost its own length, while each model is sent the system
prompt, the whole transcript and the web search results, and writes answers
far longer than the question. The expensive allowance now counts each
expensive model's characters as many times as its cost weight.
"""

import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")

from linkup import LinkupSearchTextResult  # noqa: E402

import backend.arena.limits as limits  # noqa: E402
from backend.arena.conversation import SystemMessageRead  # noqa: E402
from backend.arena.limits import Call, Charge, Identity, turn_cost  # noqa: E402
from backend.arena.litellm import litellm_messages, sent_chars  # noqa: E402
from backend.arena.web_search import merge_web_search_with_content  # noqa: E402
from tests.arena.fakes import FakeRedis, fake_redis  # noqa: E402
from utils.database.models import LLMMessageRead, UserMessageRead  # noqa: E402

WHO = Identity.of("s" * 64, "10.0.0.1")

SYSTEM = "Tu es un assistant."
FIRST, SECOND = "Bonjour ?", "Et la suite ?"


def answer(content, reasoning=None):
    return LLMMessageRead.model_construct(
        role="assistant", content=content, reasoning_content=reasoning
    )


def test_a_model_is_sent_the_system_prompt_the_transcript_and_its_answers():
    messages = [
        SystemMessageRead(content=SYSTEM),
        UserMessageRead(content=FIRST),
        # Its reasoning is not sent back to it.
        answer("Bonjour à vous.", reasoning="Je réfléchis."),
        UserMessageRead(content=SECOND),
    ]

    assert sent_chars(messages) == len(SYSTEM + FIRST + "Bonjour à vous." + SECOND)


def test_web_search_results_count_as_sent():
    results = [
        LinkupSearchTextResult(
            type="text",
            name="Le Monde",
            url="https://a.example/article",
            content="Paris est la capitale de la France.",
            favicon="",
        )
    ]
    prompt = UserMessageRead(content=FIRST, web_search_results=results)

    [sent] = litellm_messages([prompt])
    assert sent["content"] == merge_web_search_with_content(FIRST, results)
    assert sent_chars([prompt]) == len(sent["content"]) > len(FIRST) + 30


def written(content, cached=False, reasoning=""):
    return SimpleNamespace(
        content=content, reasoning_content=reasoning, is_cached=cached
    )


def counters(redis):
    return {
        (pool, identity): int(redis.get(limits.budget_key(pool, identity)) or 0)
        for pool in limits.POOLS
        for identity in WHO.identities
    }


def spent(redis, pool):
    """What the person and their network each have spent of a pool."""
    session, network = (
        counters(redis)[(pool, identity)] for identity in WHO.identities
    )
    assert session == network
    return session


def test_an_expensive_model_counts_each_character_its_weight_times():
    cheap, pricey = Call(weight=1, sent=100, written=300), Call(4, 100, 300)

    assert turn_cost([cheap, cheap]) == {"all": 800}
    assert turn_cost([cheap, pricey]) == {"all": 800, "expensive": 1600}
    # Rounded up, so a fractional weight never charges less than it says.
    assert turn_cost([Call(2.5, 1, 0)]) == {"all": 1, "expensive": 3}


def test_a_cached_answer_is_free_on_the_expensive_pool_only():
    cached = Call(4, 100, 300, cached=True)
    assert turn_cost([cached, Call(1, 100, 300)]) == {"all": 800, "expensive": 0}


def test_the_input_is_charged_up_front_and_the_answers_on_settle():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(1, 120), "b": Call(4, 150)})
        assert spent(redis, "all") == 270
        assert spent(redis, "expensive") == 600

        charge.settle(
            {"a": written("x" * 30), "b": written("y" * 40, reasoning="z" * 10)}
        )

    assert spent(redis, "all") == 270 + 30 + 50
    assert spent(redis, "expensive") == 4 * (150 + 50)


def test_web_search_results_found_after_the_reservation_are_charged_on_settle():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(1, 10), "b": Call(1, 10)})
        charge.sending("a", 2_010)
        charge.sending("b", 2_010)
        charge.settle({"a": None, "b": None})

    assert spent(redis, "all") == 4_020


def test_a_cached_side_gives_its_expensive_share_back():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(4, 100), "b": Call(1, 100)})
        charge.settle({"a": written("x" * 50, cached=True), "b": written("y" * 50)})

    assert spent(redis, "all") == 300
    assert spent(redis, "expensive") == 0


def test_a_stand_in_is_charged_as_itself_and_the_failed_model_still_counts():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(1, 100), "b": Call(1, 100)})
        # b timed out after writing 20 characters; an expensive model stands in.
        charge.replace("b", weight=4, sent=100, written=20)
        charge.settle({"a": written("x" * 10), "b": written("y" * 30)})

    assert spent(redis, "all") == 100 + 10 + (100 + 20) + (100 + 30)
    assert spent(redis, "expensive") == 4 * (100 + 30)


def test_settling_never_moves_a_reset_time():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(1, 100), "b": Call(4, 100)})
        redis.advance(600)
        charge.settle({"a": written("x" * 10), "b": written("y" * 10)})
        ttls = {redis.ttl(limits.budget_key(p, i)) for p, i in counters(redis)}

    assert ttls == {limits.WINDOW_SECONDS - 600}


def test_settling_after_the_window_closed_leaves_no_counter_without_expiry():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(1, 100), "b": Call(4, 100)})
        redis.advance(limits.WINDOW_SECONDS)
        charge.settle({"a": written("x" * 10), "b": written("y" * 10)})

        assert spent(redis, "all") == 20
        assert spent(redis, "expensive") == 40
        assert {redis.ttl(limits.budget_key(p, i)) for p, i in counters(redis)} == {
            limits.WINDOW_SECONDS
        }


def test_settling_twice_charges_once():
    with fake_redis(limits) as redis:
        charge = Charge.reserve(WHO, {"a": Call(1, 100), "b": Call(1, 100)})
        answers = {"a": written("x" * 10), "b": written("y" * 10)}
        charge.settle(answers)
        charge.settle(answers)

    assert spent(redis, "all") == 220


def test_settling_on_a_spent_allowance_still_charges_and_never_refuses():
    with fake_redis(limits) as redis:
        redis.set(limits.budget_key("expensive", WHO.personal), 10**9, ex=60)
        charge = Charge.reserve(
            WHO, {"a": Call(1, 100), "b": Call(4, 100)}, refusing=("all",)
        )
        charge.settle({"a": written("x"), "b": written("y")})

        assert counters(redis)[("expensive", WHO.personal)] == 10**9 + 4 * 101
        assert redis.ttl(limits.budget_key("expensive", WHO.personal)) == 60


def test_settling_never_raises_when_redis_is_down():
    redis = FakeRedis(pipelines_that_work=2)
    with fake_redis(limits, fake=redis):
        charge = Charge.reserve(WHO, {"a": Call(1, 100), "b": Call(1, 100)})
        charge.settle({"a": written("x"), "b": written("y")})

    assert spent(redis, "all") == 200
