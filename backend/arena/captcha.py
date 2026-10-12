"""
Altcha proof-of-work CAPTCHA integration.

Provides challenge generation, solution verification, and replay prevention via Redis.
"""

import base64
import json
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone

from altcha import Challenge, ChallengeOptions, create_challenge, verify_solution

from backend.config import (
    ALTCHA_CHALLENGE_EXPIRY_SECONDS,
    ALTCHA_MAX_NUMBER,
    ALTCHA_REPLAY_TTL_SECONDS,
    settings,
)
from utils.storage.redis import REDIS_ALTCHA_PREFIX, get_redis_client

logger = logging.getLogger("languia")


def generate_challenge(max_number: int = ALTCHA_MAX_NUMBER) -> dict:
    """
    Generate a new Altcha PoW challenge. The work grows with `max_number`, which
    is also written into the salt so the server can read it back on the
    solution.

    Returns:
        dict with algorithm, challenge, maxNumber, salt, signature
    """
    options = ChallengeOptions(
        algorithm="SHA-256",
        max_number=max_number,
        hmac_key=settings.ALTCHA_HMAC_KEY,
        expires=datetime.now(timezone.utc)
        + timedelta(seconds=ALTCHA_CHALLENGE_EXPIRY_SECONDS),
        params={"max": str(max_number)},
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

    # Replay prevention, keyed on the signed challenge rather than the payload
    # string. The payload is base64 JSON written by the client, so the same
    # solution re-encoded with other whitespace or key order is a different
    # string and would pass as new every time.
    try:
        signature = json.loads(base64.b64decode(payload).decode())["signature"]
    except (ValueError, TypeError, KeyError):
        return False, "Invalid altcha payload"
    redis_key = f"{REDIS_ALTCHA_PREFIX}{signature}"
    try:
        client = get_redis_client()
        # SET with NX returns True only if key didn't exist
        is_new = client.set(redis_key, "1", nx=True, ex=ALTCHA_REPLAY_TTL_SECONDS)
        if not is_new:
            logger.warning("Altcha replay detected")
            return False, "Challenge already used"
    except Exception as e:
        # Fail closed. Redis is the only thing standing between one solved
        # challenge and unlimited replays of it, so with Redis down the whole
        # captcha is worth nothing.
        logger.error(f"Altcha replay check failed (Redis error): {e}")
        return False, "Replay check unavailable"

    return True, None


def solved_max_number(payload: str) -> int:
    """
    The `max_number` of the challenge a payload solves, 0 when it carries none.
    It travels in the salt, which the signature covers, so a client cannot
    lower it without the solution failing verification.
    """
    try:
        salt = json.loads(base64.b64decode(payload).decode())["salt"]
        query = urllib.parse.parse_qs(salt.partition("?")[2])
        return int(query["max"][0])
    except (ValueError, TypeError, KeyError, IndexError):
        return 0
