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

from backend.config import settings
from backend.llms.models import LLMDataEnabled
from utils.storage.redis import REDIS_LLM_RESPONSES_KEY, get_redis_client, hash_content

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
    if not settings.CACHE_ENABLED:
        return None

    # Probabilistic check: skip cache with (1 - CACHE_PROBABILITY) chance
    if random.random() > settings.CACHE_PROBABILITY:
        return None

    try:
        client = get_redis_client()
        key = _responses_key(llm, system_msg, prompt)
        data = cast(Any, client.get(key))
        if not data:
            return None

        responses: list[CachedResponse] = json.loads(data)
        if not responses:
            return None

        chosen = random.choice(responses)

        # Refresh TTL on hit — popular prompts stay cached as long as they're asked
        client.expire(key, settings.CACHE_TTL)

        logger.info(f"[CACHE] Hit for {llm.id} (pool size: {len(responses)})")
        return chosen

    except Exception as e:
        logger.warning(f"[CACHE] Error reading cache: {e}")
        return None


def store_cached_response(
    llm: LLMDataEnabled, system_msg: str | None, prompt: str, response: CachedResponse
) -> None:
    """
    Store a response in the cache for this (model, prompt) pair.

    Appends to existing responses up to CACHE_MAX_RESPONSES, rotating out
    the oldest entry when full.
    """
    if not settings.CACHE_ENABLED:
        return

    try:
        client = get_redis_client()
        key = _responses_key(llm, system_msg, prompt)

        existing_data = cast(Any, client.get(key))
        responses: list[CachedResponse] = (
            json.loads(existing_data) if existing_data else []
        )

        # Add new response, evict oldest if at capacity
        responses.append(response)
        if len(responses) > settings.CACHE_MAX_RESPONSES:
            responses = responses[-settings.CACHE_MAX_RESPONSES :]

        client.set(key, json.dumps(responses), ex=settings.CACHE_TTL)
        logger.info(
            f"[CACHE] Stored response for {llm.id} (pool size: {len(responses)})"
        )

    except Exception as e:
        logger.warning(f"[CACHE] Error storing cache: {e}")
