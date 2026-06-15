import hashlib
from functools import lru_cache, wraps
from typing import Callable, Final, ParamSpec, TypeVar
from uuid import uuid4

import redis
from async_lru import alru_cache

from backend.config import settings

P = ParamSpec("P")
RT = TypeVar("RT")

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
REDIS_LLMS_DATA_CACHE_KEY: Final[str] = f"{REDIS_INSTANCE_PREFIX}llms_data"


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


def redis_cache(redis_key: str, maxsize: int = 1) -> Callable[P, RT]:
    """
    Decorator to cache a function's result based on a key stored in redis.
    Used for caching data from database for example with a multiple instances
    cache invalidation mecanism.
    Use `invalidate_cache(redis_key)` to reset cache of all instances.
    """

    def decorator(func: Callable[P, RT]) -> Callable[P, RT]:
        @alru_cache(maxsize=maxsize)
        async def cached(
            cache_key: str | None, *args: P.args, **kwargs: P.kwargs
        ) -> RT:
            return await func(*args, **kwargs)

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> RT:
            # On every calls, run the cached function with an added 'cache_key'
            # arg that, if different than last time, will not hit cache.
            cache_key = retrieve_or_set_cache_key(redis_key)
            return await cached(cache_key, *args, **kwargs)

        return wrapper

    return decorator


def retrieve_or_set_cache_key(redis_key: str) -> str:
    """
    Returns current 'redis_key' cache key if any or create one.
    Warning: If no redis, no cache mecanism.
    """
    try:
        client = get_redis_client()
        cache_key = client.get(redis_key)
        if not cache_key:
            # If no cache_key, create one.
            cache_key = invalidate_cache(redis_key)
        return cache_key
    except Exception as e:
        logger.warning(f"[CACHE] Error reading cache key '{redis_key}': {e}")
        # FIXME fallback to global variable cache key?
        # Fake key, cache will never be called
        return str(uuid4())


def invalidate_cache(redis_key: str) -> str:
    """
    Invalidate cache by updating the given 'redis_key' cache key.
    Every functions decorated with `@redis_cache(redis_key)` will be forced to
    recompute.
    """
    cache_key = str(uuid4())
    try:
        client = get_redis_client()
        client.setex(redis_key, 86400, cache_key)
        return cache_key
    except Exception as e:
        logger.warning(f"[CACHE] Error setting cache key '{redis_key}': {e}")
        return cache_key
