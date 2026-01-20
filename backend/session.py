"""
Session management and rate limiting using Redis.

This module handles per-IP rate limiting to prevent abuse of expensive model APIs
and provides session state management.
"""

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


# Draft session class and methods

# class Session:
#     session_hash: str | None
#     conversations: tuple[dict, dict]
#     # vote: Vote | None
#     # reactions: dict = []
#     ip: str | None
#     total_input_chars: int = 0


# def save_session(session: Session):
#     r.hset(
#         f"session:{session.session_hash}",
#         mapping={
#             "conversations": session.conversations,
#             "ip": session.ip,
#         },
#     )
#     r.hgetall(f"session:{session.session_hash}")


#     r.hset(f'session:{session.session_hash}', mapping={
#         'name': 'John',
#         "surname": 'Smith',
#         "company": 'Redis',
#         "age": 29
#     })
#     r.hgetall(f'session:{session.session_hash}')
#     # True
#     total_input_chars = r.hget(f'session:{session.session_hash}', "total_input_chars")

#     r.hset(f'session:{session.session_hash}', mapping={
#         "total_input_chars": 29
#     })
#     # True
#     r.hgetall('user-session:123')
