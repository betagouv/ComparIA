"""
The answer cache: what shares a key, when an answer is stored, and when one
is served (no network, no real Redis).
"""

import asyncio
import unicodedata
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from linkup import LinkupSearchTextResult

import backend.arena.cache as cache
import backend.arena.conversation as conversation
import backend.arena.web_search as web_search
from backend.arena.cache import (
    CachedResponse,
    get_cached_response,
    store_cached_response,
)
from backend.arena.conversation import SystemMessageRead, bot_response_async
from backend.config import settings
from backend.llms.models import LitellmEndpoint
from tests.arena.fakes import fake_redis
from utils.database.models import UserMessageRead
from utils.storage.redis import REDIS_LLM_CACHE_SEEN_KEY, hash_content

PROMPT = "Quelle est la capitale de la Moldavie ?"
ANSWER = CachedResponse(content="Chisinau.", reasoning="", output_tokens=3)
LIVE_ANSWER = "Chisinau, sur le Bîc."


def model(api_model_id="small-2506", base_url="http://127.0.0.1:9/v1", **changes):
    fields = {
        "id": "small-llm",
        "human_id": "small-llm",
        "system_prompt": None,
        "litellm_endpoint": LitellmEndpoint(
            model=f"openai/{api_model_id}",
            base_url=base_url,
            api_key="dummy",
            api_version=None,
        ),
        "endpoint": SimpleNamespace(api_model_id=api_model_id),
    }
    return SimpleNamespace(**(fields | changes))


def seen_twice(llm, prompt, system_msg=None):
    """Store an answer as a second turn sending the prompt would, so that a
    miss after it comes from the key and not from an empty cache."""
    store_cached_response(llm, system_msg, prompt, uuid4(), ANSWER)
    store_cached_response(llm, system_msg, prompt, uuid4(), ANSWER)
    assert get_cached_response(llm, system_msg, prompt) == ANSWER


@pytest.fixture(autouse=True)
def always_served(monkeypatch):
    monkeypatch.setattr(settings, "CACHE_PROBABILITY", 1.0)
    monkeypatch.setattr(settings, "MOCK_RESPONSE", False)


@pytest.fixture
def redis():
    with fake_redis(cache, web_search) as fake:
        yield fake


def test_a_new_model_version_misses(redis):
    seen_twice(model(), PROMPT)
    assert get_cached_response(model(api_model_id="small-2509"), None, PROMPT) is None


def test_a_new_endpoint_misses(redis):
    seen_twice(model(), PROMPT)
    moved = model(base_url="https://api.example.org/v1")
    assert get_cached_response(moved, None, PROMPT) is None


def test_a_new_system_prompt_misses(redis):
    seen_twice(model(), PROMPT, system_msg="Réponds en une phrase.")
    assert get_cached_response(model(), "Réponds en détail.", PROMPT) is None


def test_the_system_prompt_sent_counts_not_the_one_on_the_model(redis):
    seen_twice(model(), PROMPT, system_msg="Réponds en une phrase.")
    edited = model(system_prompt="Réponds en détail.")
    assert get_cached_response(edited, "Réponds en une phrase.", PROMPT) == ANSWER


def test_spacing_and_composed_accents_hit(redis):
    seen_twice(model(), "Où se trouve   Chişinău ? \r\nEn Moldavie\n")
    decomposed = unicodedata.normalize("NFD", "où se trouve chişinău ?\nen moldavie")
    assert decomposed != unicodedata.normalize("NFC", decomposed)
    assert get_cached_response(model(), None, decomposed) == ANSWER


def test_line_breaks_and_indentation_still_tell_prompts_apart(redis):
    code = "def f():\n    return 1"
    seen_twice(model(), code)
    assert get_cached_response(model(), None, "def f(): return 1") is None
    assert get_cached_response(model(), None, "def f():\nreturn 1") is None


def test_punctuation_still_tells_prompts_apart(redis):
    seen_twice(model(), "Paris ?")
    assert get_cached_response(model(), None, "Paris.") is None


def test_the_first_sighting_stores_nothing_and_the_second_does(redis):
    store_cached_response(model(), None, PROMPT, uuid4(), ANSWER)
    assert get_cached_response(model(), None, PROMPT) is None

    store_cached_response(model(), None, PROMPT, uuid4(), ANSWER)
    assert get_cached_response(model(), None, PROMPT) == ANSWER


def test_both_answers_of_one_turn_count_once(redis):
    turn_id = uuid4()
    store_cached_response(model(), None, PROMPT, turn_id, ANSWER)
    store_cached_response(model(id="other-llm"), None, PROMPT, turn_id, ANSWER)
    # A retry runs the same turn again.
    store_cached_response(model(), None, PROMPT, turn_id, ANSWER)

    assert get_cached_response(model(), None, PROMPT) is None
    assert get_cached_response(model(id="other-llm"), None, PROMPT) is None


def test_a_prompt_asked_again_stays_seen(redis):
    seen = REDIS_LLM_CACHE_SEEN_KEY.format(prompt_hash=hash_content(PROMPT))
    store_cached_response(model(), None, PROMPT, uuid4(), ANSWER)
    redis.advance(settings.CACHE_TTL - 60)

    store_cached_response(model(), None, PROMPT, uuid4(), ANSWER)
    assert redis.ttl(seen) == settings.CACHE_TTL


def test_a_hit_keeps_the_answers_for_another_ttl(redis):
    seen_twice(model(), PROMPT)
    redis.advance(settings.CACHE_TTL - 60)
    assert get_cached_response(model(), None, PROMPT) == ANSWER

    redis.advance(120)
    assert get_cached_response(model(), None, PROMPT) == ANSWER


def test_probability_zero_never_serves(redis, monkeypatch):
    seen_twice(model(), PROMPT)
    monkeypatch.setattr(settings, "CACHE_PROBABILITY", 0.0)
    # random() can return 0.0, the lowest draw there is.
    monkeypatch.setattr(cache.random, "random", lambda: 0.0)
    assert get_cached_response(model(), None, PROMPT) is None


def test_web_search_results_last_an_hour(redis):
    web_search.store_cached_search_results(PROMPT, [])
    [key] = redis.store
    assert redis.ttl(key) == settings.WEB_SEARCH_CACHE_TTL == 3600


def first_turn(prompt, web_search_results=None):
    return SimpleNamespace(
        id=uuid4(),
        user_msg=UserMessageRead(content=prompt, web_search_results=web_search_results),
    )


@pytest.fixture
def provider(monkeypatch):
    """Answers every call with LIVE_ANSWER and counts the calls."""
    calls = []

    async def litellm_stream_iter(llm, messages, msg, **_kwargs):
        calls.append(messages)
        msg.created_at = msg.responded_at = msg.updated_at = datetime.now()
        msg.content = LIVE_ANSWER
        msg.tokens = 7
        yield msg

    monkeypatch.setattr(conversation, "litellm_stream_iter", litellm_stream_iter)
    # A cached answer waits as a provider would; not here.
    monkeypatch.setattr(conversation.random, "uniform", lambda *_: 0.001)
    monkeypatch.setattr(conversation, "CACHED_CHUNK_DELAY", 0)
    return calls


def chunks(turn, system_msg=None):
    messages = [turn.user_msg]
    if system_msg:
        messages.insert(0, SystemMessageRead(content=system_msg))

    async def run():
        return [
            msg.model_copy()
            async for msg in bot_response_async("a", model(), turn, 0, messages)
        ]

    return asyncio.run(run())


def answer(turn, system_msg=None):
    return chunks(turn, system_msg)[-1]


def test_a_first_turn_is_served_from_the_cache(redis, provider):
    seen_twice(model(), PROMPT)
    final = answer(first_turn(PROMPT))
    assert final.is_cached
    assert final.content == ANSWER["content"]
    assert provider == []


def test_a_first_turn_reads_the_system_prompt_it_sends(redis, provider):
    seen_twice(model(), PROMPT, system_msg="Réponds en une phrase.")
    assert not answer(first_turn(PROMPT)).is_cached
    assert answer(first_turn(PROMPT), "Réponds en une phrase.").is_cached


def test_a_cached_answer_arrives_like_a_live_one(redis, provider):
    reasoning = "La Moldavie est entre la Roumanie et l'Ukraine. " * 3
    content = "La capitale de la Moldavie est Chisinau. " * 3
    store = CachedResponse(content=content, reasoning=reasoning, output_tokens=40)
    store_cached_response(model(), None, PROMPT, uuid4(), store)
    store_cached_response(model(), None, PROMPT, uuid4(), store)

    sent = chunks(first_turn(PROMPT))

    final = sent[-1]
    assert final.is_cached
    assert final.created_at < final.responded_at <= final.updated_at
    # The reasoning comes in pieces, before any content, as from a provider.
    assert len(reasoning) > len(sent[0].reasoning_content) > 0
    assert sent[0].content == ""
    assert (final.reasoning_content, final.content) == (
        reasoning.strip(),
        content.strip(),
    )


def test_a_web_search_turn_neither_reads_nor_writes(redis, provider):
    seen_twice(model(), PROMPT)
    stored = dict(redis.store)
    results = [
        LinkupSearchTextResult(
            type="text", name="", url="https://example.org", content="", favicon=""
        )
    ]

    final = answer(first_turn(PROMPT, results))
    assert not final.is_cached
    assert final.content == LIVE_ANSWER

    answer(first_turn(PROMPT, results))
    assert redis.store == stored


def test_a_fake_answer_neither_reads_nor_writes(redis, provider, monkeypatch):
    """On a Redis a local run shares with a deploy, a stored fake answer
    would be served to people for real prompts."""
    monkeypatch.setattr(settings, "MOCK_RESPONSE", True)
    seen_twice(model(), PROMPT)
    stored = dict(redis.store)

    assert not answer(first_turn(PROMPT)).is_cached
    answer(first_turn(PROMPT))
    assert redis.store == stored
