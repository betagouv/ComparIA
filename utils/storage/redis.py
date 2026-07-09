import hashlib
from functools import lru_cache
from typing import Final

import redis

from backend.config import settings

# TODO drop DEFAULT_COUNTRY_PORTAL env var + add REDIS_INSTANCE_PREFIX?
REDIS_INSTANCE_PREFIX: Final[str] = (
    f"{settings.DEFAULT_COUNTRY_PORTAL}:" if settings.DEFAULT_COUNTRY_PORTAL else ""
)

# Redis keys (all namespaced by instance portal prefix)
REDIS_COMPARISON_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}comparison:{{id}}"
REDIS_USER_CHAR_COUNT: Final[str] = f"{REDIS_INSTANCE_PREFIX}ip:{{ip}}"
REDIS_CUSTOM_HOURLY_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}custom_hourly:{{ip}}"
REDIS_CUSTOM_DAILY_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}custom_daily:{{ip}}"
REDIS_BLOCKED_COUNT_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}guardrail_blocked:{{ip}}"
REDIS_VOTE_COUNT_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}count"
REDIS_RANKING_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}rankings_and_prefs"
REDIS_LLM_RESPONSES_KEY: Final[str] = (
    f"{REDIS_INSTANCE_PREFIX}llm_cache:{{model_name}}:{{prompt_hash}}"
)
REDIS_ALTCHA_PREFIX: Final[str] = f"{REDIS_INSTANCE_PREFIX}altcha:"
REDIS_WEB_SEARCH_KEY: Final[str] = (
    f"{REDIS_INSTANCE_PREFIX}web_search_cache:{{prompt_hash}}"
)
REDIS_MAINTENANCE_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}maintenance_mode"


@lru_cache
def get_redis_client() -> redis.Redis:
    try:
        # Initialize Redis client
        client = redis.Redis(
            host=settings.COMPARIA_REDIS_HOST,
            port=6379,
            decode_responses=True,  # returns strings instead of bytes
        )

        # Fail if we don't have a working redis
        if not (response := client.ping()):
            raise Exception(f"{response}")

        return client
    except Exception as e:
        raise Exception(f"Redis Connection Error: {e}")


def hash_content(content: str) -> str:
    """Normalize and hash content."""
    normalized = content.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def get_maintenance_mode() -> bool:
    return get_redis_client().get(REDIS_MAINTENANCE_KEY) == "1"


def maintenance_key_for_instance(instance: str) -> str:
    """Build the maintenance mode key for an arbitrary instance (fr, da, ...),
    regardless of the current process' own DEFAULT_COUNTRY_PORTAL."""
    return f"{instance}:maintenance_mode"
