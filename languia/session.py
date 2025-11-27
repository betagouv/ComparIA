"""
Session management and rate limiting using Redis.

This module handles per-IP rate limiting to prevent abuse of expensive model APIs
and provides session state management.
"""

import redis
import os
import logging

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


def set_do_not_track(session_hash: str, cohorts: str = "do-not-track"):
    """
    Stocke dans Redis une indication de ne pas suivre pour une session donnée.

    Args:
        session_hash: Identifiant unique de la session
        cohorts: Nom de la cohorte (par défaut "do-not-track")

    Returns:
        bool: True si l'opération a réussi, False sinon
    """
    if not redis_host:
        return False

    try:
        # Stocke la clé avec une expiration de 24 heures
        r.setex(f"do_no_track:{session_hash}", 86400, cohorts)
        return True
    except Exception as e:
        logger = logging.getLogger("languia")
        logger.error(f"Error setting do_not_track in Redis: {e}")
        return False


def get_do_not_track(session_hash: str):
    """
    Vérifie si une session a une indication de ne pas suivre.

    Args:
        session_hash: Identifiant unique de la session

    Returns:
        dict: Dictionnaire avec les clés:
            - 'do_not_track': bool (True si trouvé, False sinon)
            - 'cohorts': str|None (Nom de la cohorte si trouvée, None sinon)
            - 'status': str (description claire du statut)
    """
    if not redis_host:
        return {"do_not_track": False, "cohorts": None, "status": "redis not available"}

    try:
        cohorts = r.get(f"do_no_track:{session_hash}")
        if cohorts:
            return {
                "do_not_track": True,
                "cohorts": cohorts,
                "status": f"found and cohorts={cohorts}",
            }
    except Exception as e:
        logger = logging.getLogger("languia")
        logger.error(f"Error getting do_not_track from Redis: {e}")
        return {
            "do_not_track": False,
            "cohorts": None,
            "status": "false, cohorts not found in do not track so you can track (Redis error)",
        }


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
