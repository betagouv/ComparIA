from functools import lru_cache

import redis

from backend.config import settings


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
