"""
Session management and rate limiting using Redis.

This module handles per-IP rate limiting to prevent abuse of expensive model APIs
and provides session state management.
"""

import redis
import os

# Redis connection configuration
redis_host = os.getenv("COMPARIA_REDIS_HOST", False)
# Alternative: redis_host = os.environ("COMPARIA_REDIS_HOST", 'languia-redis')

# Initialize Redis client (decode_responses=True returns strings instead of bytes)
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

from languia.config import RATELIMIT_PRICEY_MODELS_INPUT


def increment_input_chars(ip: str, input_chars: int):
    """
    Track input character count per IP address for rate limiting.

    Increments a counter in Redis for the given IP and sets expiry to 2 hours.
    This prevents users from overloading expensive model APIs.

    Args:
        ip: User's IP address
        input_chars: Number of input characters to add to counter

    Returns:
        bool: False if Redis not configured, True otherwise
    """
    if not redis_host:
        return False
    # Increment counter under key "ip:{ip}"
    r.incrby(f"ip:{ip}", input_chars)
    # Set counter to expire in 2 hours (3600 * 2 seconds)
    r.expire(f"ip:{ip}", 3600 * 2)
    return True


def is_ratelimited(ip: str):
    """
    Check if an IP address has exceeded rate limit for expensive models.

    Args:
        ip: User's IP address

    Returns:
        bool: True if IP has exceeded limit (2x RATELIMIT_PRICEY_MODELS_INPUT), False otherwise
    """
    counter = r.get(f"ip:{ip}")
    # Rate limit is 2x the configured limit for pricey models
    if counter and int(counter) > RATELIMIT_PRICEY_MODELS_INPUT * 2:
        return True
    else:
        return False


class Session:
    """
    Represents a user session with conversation history and metadata.

    Attributes:
        session_hash: Unique identifier for the session (from Gradio)
        conversations: Tuple of two conversation dicts (model A and B)
        ip: User's IP address
        total_input_chars: Total character count for rate limiting
    """
    session_hash: str | None
    conversations: tuple[dict, dict]
    # Future fields for votes and reactions
    # vote: Vote | None
    # reactions: dict = []
    ip: str | None
    total_input_chars: int = 0


def save_session(session: Session):
    """
    Save session state to Redis for later retrieval.

    Args:
        session: Session object to save
    """
    # Store session as Redis hash with conversations and IP
    r.hset(
        f"session:{session.session_hash}",
        mapping={
            "conversations": session.conversations,
            "ip": session.ip,
        },
    )
    # Verify the save by retrieving the data
    r.hgetall(f"session:{session.session_hash}")


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
