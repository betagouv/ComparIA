"""
Altcha proof-of-work CAPTCHA integration.

Provides challenge generation, solution verification, and replay prevention via Redis.
"""

import logging
from datetime import datetime, timedelta, timezone

from altcha import ChallengeOptions, Challenge, create_challenge, verify_solution

from backend.config import (
    ALTCHA_CHALLENGE_EXPIRY_SECONDS,
    ALTCHA_MAX_NUMBER,
    ALTCHA_REPLAY_TTL_SECONDS,
    settings,
)
from utils.storage.redis import get_redis_client

logger = logging.getLogger("languia")

REDIS_PREFIX = "altcha:"


def generate_challenge() -> dict:
    """
    Generate a new Altcha PoW challenge.

    Returns:
        dict with algorithm, challenge, maxNumber, salt, signature
    """
    options = ChallengeOptions(
        algorithm="SHA-256",
        max_number=ALTCHA_MAX_NUMBER,
        hmac_key=settings.ALTCHA_HMAC_KEY,
        expires=datetime.now(timezone.utc)
        + timedelta(seconds=ALTCHA_CHALLENGE_EXPIRY_SECONDS),
    )
    challenge: Challenge = create_challenge(options)
    return challenge.to_dict()


def verify_altcha_token(payload: str) -> tuple[bool, str | None]:
    """
    Verify an Altcha solution payload with replay prevention.

    Args:
        payload: Base64-encoded Altcha solution payload from the client widget

    Returns:
        (True, None) if valid, (False, error_message) if invalid
    """
    # Verify cryptographic solution
    ok, error = verify_solution(
        payload=payload,
        hmac_key=settings.ALTCHA_HMAC_KEY,
        check_expires=True,
    )
    if not ok:
        logger.warning(f"Altcha verification failed: {error}")
        return False, error

    # Replay prevention: check if this payload was already used
    redis_key = f"{REDIS_PREFIX}{payload[:64]}"
    try:
        client = get_redis_client()
        # SET with NX returns True only if key didn't exist
        is_new = client.set(redis_key, "1", nx=True, ex=ALTCHA_REPLAY_TTL_SECONDS)
        if not is_new:
            logger.warning("Altcha replay detected")
            return False, "Challenge already used"
    except Exception as e:
        # If Redis is down, allow the request (fail open) but log it
        logger.error(f"Altcha replay check failed (Redis error): {e}")

    return True, None
