"""
Response caching for LLM API calls using Redis.

Caches first-turn responses per (model, prompt) pair to reduce API costs.
Stores multiple responses per key to preserve diversity, and serves cached
responses with configurable probability to avoid determinism.
"""

import hashlib
import json
import logging
import random
from typing import Any, TypedDict, cast
from uuid import UUID

from backend.config import settings
from backend.llms.models import LLMDataEnabled
from utils.storage.redis import (
    REDIS_LLM_CACHE_SEEN_KEY,
    REDIS_LLM_RESPONSES_KEY,
    get_redis_client,
    hash_content,
)

logger = logging.getLogger("languia")


class CachedResponse(TypedDict):
    content: str
    reasoning: str
    output_tokens: int | None


def model_fingerprint(llm: LLMDataEnabled, system_msg: str | None) -> str:
    """
    Changes when an admin points the model at another version, provider or
    endpoint, or edits its system prompt, so the answers written before stop
    being served. The system prompt is the one the comparison sends, which
    can be older than the model's current one.
    """
    endpoint = llm.litellm_endpoint
    identity = json.dumps([endpoint.model, endpoint.base_url, system_msg])
    return hashlib.sha256(identity.encode()).hexdigest()[:16]


def _responses_key(llm: LLMDataEnabled, system_msg: str | None, prompt: str) -> str:
    return REDIS_LLM_RESPONSES_KEY.format(
        llm_id=llm.id,
        fingerprint=model_fingerprint(llm, system_msg),
        prompt_hash=hash_content(prompt),
    )


def get_cached_response(
    llm: LLMDataEnabled, system_msg: str | None, prompt: str
) -> CachedResponse | None:
    """
    Try to get a cached response for this (model, prompt) pair.

    Returns a random cached response with CACHE_PROBABILITY chance,
    or None if cache miss or probability check fails.
    """
    # Probabilistic check: skip cache with (1 - CACHE_PROBABILITY) chance
    if random.random() >= settings.CACHE_PROBABILITY:
        return None

    try:
        key = _responses_key(llm, system_msg, prompt)
        pipe = get_redis_client().pipeline()
        pipe.get(key)
        # Refresh TTL on hit, so popular prompts stay cached as long as they're
        # asked. On a miss there is no key and this does nothing.
        pipe.expire(key, settings.CACHE_TTL)
        data, _ = cast(list[Any], pipe.execute())
        if not data:
            return None

        responses: list[CachedResponse] = json.loads(data)
        if not responses:
            return None

        chosen = random.choice(responses)
        logger.info(f"[CACHE] Hit for {llm.id} (pool size: {len(responses)})")
        return chosen

    except Exception as e:
        logger.warning(f"[CACHE] Error reading cache: {e}")
        return None


def store_cached_response(
    llm: LLMDataEnabled,
    system_msg: str | None,
    prompt: str,
    turn_id: UUID,
    response: CachedResponse,
) -> None:
    """
    Store a response in the cache for this (model, prompt) pair, from the
    second turn that sends the prompt on.

    Appends to existing responses up to CACHE_MAX_RESPONSES, rotating out
    the oldest entry when full.
    """
    try:
        client = get_redis_client()
        seen_key = REDIS_LLM_CACHE_SEEN_KEY.format(prompt_hash=hash_content(prompt))
        key = _responses_key(llm, system_msg, prompt)

        pipe = client.pipeline()
        # Remember the first turn that sent this prompt. Both answers of that
        # turn, and a retry of it, count as one sighting.
        pipe.set(seen_key, str(turn_id), ex=settings.CACHE_TTL, nx=True)
        pipe.get(seen_key)
        pipe.get(key)
        first_sighting, seen_by, existing_data = cast(list[Any], pipe.execute())
        if first_sighting or seen_by == str(turn_id):
            return

        responses: list[CachedResponse] = (
            json.loads(existing_data) if existing_data else []
        )

        # Add new response, evict oldest if at capacity
        responses.append(response)
        if len(responses) > settings.CACHE_MAX_RESPONSES:
            responses = responses[-settings.CACHE_MAX_RESPONSES :]

        pipe = client.pipeline()
        # Kept as long as the prompt is asked, like the answers it lets in.
        pipe.expire(seen_key, settings.CACHE_TTL)
        pipe.set(key, json.dumps(responses), ex=settings.CACHE_TTL)
        pipe.execute()
        logger.info(
            f"[CACHE] Stored response for {llm.id} (pool size: {len(responses)})"
        )

    except Exception as e:
        logger.warning(f"[CACHE] Error storing cache: {e}")
