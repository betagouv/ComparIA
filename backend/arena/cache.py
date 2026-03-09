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
from typing import TypedDict

from backend.config import settings
from backend.session import get_redis_client

logger = logging.getLogger("languia")

CACHE_KEY_PREFIX = "llm_cache"


class CachedResponse(TypedDict):
    content: str
    reasoning: str
    output_tokens: int | None


def _cache_key(model_name: str, prompt: str) -> str:
    """Build a Redis key from model name and normalized prompt."""
    normalized = prompt.strip().lower()
    prompt_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"{CACHE_KEY_PREFIX}:{model_name}:{prompt_hash}"


def get_cached_response(model_name: str, prompt: str) -> CachedResponse | None:
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
        key = _cache_key(model_name, prompt)
        data = client.get(key)
        if not data:
            return None

        responses: list[CachedResponse] = json.loads(data)
        if not responses:
            return None

        chosen = random.choice(responses)

        # Refresh TTL on hit — popular prompts stay cached as long as they're asked
        client.expire(key, settings.CACHE_TTL)

        logger.info(
            f"[CACHE] Hit for {model_name} (pool size: {len(responses)})"
        )
        return chosen

    except Exception as e:
        logger.warning(f"[CACHE] Error reading cache: {e}")
        return None


def store_cached_response(
    model_name: str, prompt: str, response: CachedResponse
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
        key = _cache_key(model_name, prompt)

        existing_data = client.get(key)
        responses: list[CachedResponse] = (
            json.loads(existing_data) if existing_data else []
        )

        # Add new response, evict oldest if at capacity
        responses.append(response)
        if len(responses) > settings.CACHE_MAX_RESPONSES:
            responses = responses[-settings.CACHE_MAX_RESPONSES :]

        client.setex(key, settings.CACHE_TTL, json.dumps(responses))
        logger.info(
            f"[CACHE] Stored response for {model_name} (pool size: {len(responses)})"
        )

    except Exception as e:
        logger.warning(f"[CACHE] Error storing cache: {e}")
