"""
Session management and rate limiting using Redis.

This module handles per-IP rate limiting to prevent abuse of expensive model APIs
and provides session state management.
"""

import logging
import os
from typing import List

import redis
from pydantic import BaseModel

from backend.config import RATELIMIT_PRICEY_MODELS_INPUT, settings

try:
    # Redis connection configuration
    redis_host = settings.COMPARIA_REDIS_HOST
    # Alternative: redis_host = os.environ("COMPARIA_REDIS_HOST", 'languia-redis')

    # Initialize Redis client (decode_responses=True returns strings instead of bytes)
    r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

    # Fail if we don't have a working redis
    response = r.ping()
    if not r.ping():
        logger = logging.getLogger("languia")
        logger.error(f"Erreur de connection au redis - {response}")

except Exception as e:
    raise Exception(f"Redis Connection Error {e}")


class CohortRequest(BaseModel):
    session_hash: str
    cohorts: str


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


def store_cohorts_redis(session_hash: str, cohorts_comma_separated: str):
    """
    Stocke dans Redis une indication de ne pas suivre pour une session donnée.

    Args:
        session_hash: Identifiant unique de la session
        cohorts_comma_separated: Liste des cohortes à stocker sous forme d'une chaine comma separated

    Returns:
        bool: True si l'opération a réussi, False sinon
    """
    if not redis_host:
        logger = logging.getLogger("languia")
        logger.warning("[COHORT] Redis not configured (COMPARIA_REDIS_HOST not set)")
        return False
    logger = logging.getLogger("languia")
    try:
        # Stocke la clé avec une expiration de 24 heures
        expire_time = 86400
        logger.info(
            f"[COHORT] Storing in Redis: cohorts:{session_hash} = {cohorts_comma_separated} (expire={expire_time}s)"
        )
        r.setex(f"cohorts:{session_hash}", expire_time, cohorts_comma_separated)
        logger.info(f"[COHORT] Successfully stored in Redis")
        return True
    except Exception as e:
        logger.error(f"[COHORT] Error storing cohorts in Redis: {e}")
        return False


def retrieve_cohorts_redis(session_hash: str):
    """
    Vérifie si une session a une indication de ne pas suivre.

    Args:
        session_hash: Identifiant unique de la session

    Returns:
        - 'cohorts_comma_separated': str|None - Optionnel, Nom des cohortes comma separated ou None
    """
    if not redis_host:
        return None
    logger = logging.getLogger("languia")
    try:
        cohorts_comma_separated = r.get(f"cohorts:{session_hash}")
        logger.info(
            f"[COHORT] Retrieved from Redis for {session_hash}: {cohorts_comma_separated}"
        )

        if cohorts_comma_separated:
            return cohorts_comma_separated
        else:
            return None

    except Exception as e:
        logger.error(f"[COHORT] Error getting cohort list from Redis: {e}")
        return None


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
