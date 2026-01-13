"""
Session management and rate limiting using Redis.

This module handles per-IP rate limiting to prevent abuse of expensive model APIs
and provides session state management.
"""

import logging
import os
from functools import lru_cache

import redis
from pydantic import BaseModel

from backend.config import RATELIMIT_PRICEY_MODELS_INPUT, settings

logger = logging.getLogger("languia")


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


class CohortRequest(BaseModel):
    session_hash: str
    cohorts: str


def store_cohorts_redis(session_hash: str, cohorts_comma_separated: str) -> bool:
    """
    Stocke dans Redis une indication de ne pas suivre pour une session donnée.

    Args:
        session_hash: Identifiant unique de la session
        cohorts_comma_separated: Liste des cohortes à stocker sous forme d'une chaine comma separated

    Returns:
        bool: True si l'opération a réussi, False sinon
    """
    if not redis_host:
        logger.warning("[COHORT] Redis not configured (COMPARIA_REDIS_HOST not set)")
        return False

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


def retrieve_cohorts_redis(session_hash: str) -> str | None:
    """
    Vérifie si une session a une indication de ne pas suivre.

    Args:
        session_hash: Identifiant unique de la session

    Returns:
        - 'cohorts_comma_separated': str|None - Optionnel, Nom des cohortes comma separated ou None
    """
    if not redis_host:
        return None

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
