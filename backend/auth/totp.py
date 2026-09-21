"""Authenticator app (TOTP) second factor for admins.

The secret an admin scans is stored encrypted (see `utils.secrets`). Codes
are RFC 6238 defaults (SHA-1, 6 digits, 30 s), the only combination every
authenticator app honours.
"""

import hmac
import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import pyotp
import segno
from sqlalchemy import delete as sa_delete
from sqlalchemy import func
from sqlmodel import select

from backend.auth.services import (
    _create_session,
    _hash,
    _revoke_other_user_sessions,
)
from utils.database.models.auth import TotpChallenge, User, UserTotp
from utils.database.session import get_session
from utils.secrets import decrypt_secret, encrypt_secret, needs_reencryption

logger = logging.getLogger("languia")

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6
# One step each side: phones drift, and a code typed at the end of its window
# lands at the start of the next.
_TOTP_VALID_WINDOW = 1
_TOTP_SETUP_TTL_MINUTES = 15
_TOTP_CHALLENGE_MAX_ATTEMPTS = 5
# Per account, across challenges: a fresh challenge only costs an email code,
# so the per-challenge count alone would leave thousands of guesses a month.
_TOTP_MAX_FAILS_PER_USER_PER_HOUR = 15
_TOTP_CHALLENGE_WINDOW = timedelta(hours=1)
_DEFAULT_ISSUER = "ComparIA"


class TotpCodeRequiredError(Exception):
    """Changing an enrolled authenticator needs a code from the current one."""


class InvalidTotpCodeError(Exception):
    pass


class TotpSetupMissingError(Exception):
    """No secret waiting to be confirmed, or the one shown has expired."""


class TotpChallengeExpiredError(Exception):
    """The half-signed-in state is gone: expired, used, out of attempts, or
    the authenticator was reset meanwhile. The user starts over."""


# Codes


def issuer_from(platform_name: str | None) -> str:
    """The otpauth label is `issuer:account`, and some apps split on the first
    colon whatever the encoding, so the issuer must not carry one."""
    cleaned = re.sub(r"[:\s]+", " ", platform_name or "").strip()
    return cleaned or _DEFAULT_ISSUER


def provisioning_uri(secret: str, email: str, issuer: str) -> str:
    return pyotp.TOTP(
        secret, digits=TOTP_DIGITS, interval=TOTP_STEP_SECONDS
    ).provisioning_uri(name=email, issuer_name=issuer)


def qr_data_uri(uri: str) -> str:
    # Explicit light module colour: the page may be in dark mode and a
    # transparent background does not scan.
    return segno.make(uri, error="m").svg_data_uri(scale=4, light="#fff", dark="#000")


def current_step(now: float | None = None) -> int:
    return int(now if now is not None else time.time()) // TOTP_STEP_SECONDS


def matching_step(
    secret: str,
    code: str,
    now: float | None = None,
    last_used_step: int | None = None,
) -> int | None:
    """The time step `code` belongs to, or None.

    Every candidate is compared before answering, in constant time, and a
    step at or before the last accepted one is refused so a code seen once
    cannot be replayed inside its window.
    """
    # ASCII only: `\d` would also match other scripts' digits, which the
    # constant-time comparison then refuses with a TypeError.
    if not re.fullmatch(rf"[0-9]{{{TOTP_DIGITS}}}", code):
        return None
    totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_STEP_SECONDS)
    step = current_step(now)
    matched = None
    for candidate in range(step - _TOTP_VALID_WINDOW, step + _TOTP_VALID_WINDOW + 1):
        expected = totp.generate_otp(candidate)
        if hmac.compare_digest(expected, code):
            matched = candidate
    if matched is None:
        return None
    if last_used_step is not None and matched <= last_used_step:
        return None
    return matched


# Enrolment


@dataclass
class TotpSetup:
    secret: str
    otpauth_uri: str
    qr_svg: str


async def has_confirmed_totp(user_id: uuid.UUID) -> bool:
    async with get_session() as session:
        result = await session.exec(
            select(UserTotp.id).where(
                UserTotp.user_id == user_id, UserTotp.confirmed_at.is_not(None)
            )
        )
        return result.first() is not None


async def _get_user_totp(session, user_id: uuid.UUID) -> UserTotp | None:
    """The user's row, locked until the transaction ends: two requests
    checking codes at once must not both pass on the same time step, and two
    device changes must not interleave."""
    result = await session.exec(
        select(UserTotp).where(UserTotp.user_id == user_id).with_for_update()
    )
    return result.first()


def _check_live_code(totp: UserTotp, code: str) -> int:
    """SecretUnreadableError passes through: it is not a wrong code."""
    if not totp.secret_encrypted:
        raise InvalidTotpCodeError()
    secret = decrypt_secret(totp.secret_encrypted)
    step = matching_step(secret, code, last_used_step=totp.last_used_step)
    if step is None:
        raise InvalidTotpCodeError()
    return step


async def start_totp_setup(
    user: User, current_code: str | None, platform_name: str | None
) -> TotpSetup:
    """Mint a secret to scan. It only counts once `confirm_totp_setup` has
    seen a code from it; until then the live secret, if any, stays in force."""
    now = datetime.now()
    secret = pyotp.random_base32()
    async with get_session() as session:
        totp = await _get_user_totp(session, user.id)
        if totp is None:
            totp = UserTotp(user_id=user.id)
        elif totp.confirmed_at is not None:
            if not current_code:
                raise TotpCodeRequiredError()
            totp.last_used_step = _check_live_code(totp, current_code)

        totp.pending_secret_encrypted = encrypt_secret(secret)
        totp.pending_created_at = now
        totp.updated_at = now
        session.add(totp)
        await session.commit()

    issuer = issuer_from(platform_name)
    uri = provisioning_uri(secret, user.email, issuer)
    return TotpSetup(secret=secret, otpauth_uri=uri, qr_svg=qr_data_uri(uri))


async def confirm_totp_setup(user: User, code: str, current_session_token: str) -> None:
    """Promote the pending secret once its owner proves they hold it, then
    sign every other session of the account out."""
    now = datetime.now()
    async with get_session() as session:
        totp = await _get_user_totp(session, user.id)
        if (
            totp is None
            or not totp.pending_secret_encrypted
            or totp.pending_created_at is None
            or totp.pending_created_at + timedelta(minutes=_TOTP_SETUP_TTL_MINUTES)
            < now
        ):
            raise TotpSetupMissingError()

        secret = decrypt_secret(totp.pending_secret_encrypted)
        step = matching_step(secret, code)
        if step is None:
            raise InvalidTotpCodeError()

        totp.secret_encrypted = totp.pending_secret_encrypted
        totp.pending_secret_encrypted = None
        totp.pending_created_at = None
        totp.confirmed_at = now
        totp.last_used_step = step
        totp.updated_at = now
        session.add(totp)
        # Same transaction as the confirmation: an authenticator in force
        # with the old sessions still alive would let them into the admin
        # area without ever presenting a code.
        await _revoke_other_user_sessions(session, user.id, current_session_token)
        await session.commit()


# Sign-in challenge


async def verify_totp_challenge(
    token: str,
    code: str,
    ip: str,
    user_agent: str | None,
    anonymous_user_hash: str | None = None,
) -> str:
    """Turn a challenge into a session, or say why not.

    A wrong code costs an attempt even when the caller's transaction fails
    later: the counter is committed before the error goes out. A secret no
    key opens raises SecretUnreadableError without costing one.
    """
    now = datetime.now()
    async with get_session() as session:
        # Locked, so concurrent attempts on one challenge queue up: the
        # attempt counter cannot lose increments and a code cannot be
        # consumed twice. The user's TOTP row is locked next, always in this
        # order, so two challenges of one user cannot deadlock.
        result = await session.exec(
            select(TotpChallenge)
            .where(
                TotpChallenge.token_hash == _hash(token),
                TotpChallenge.used_at.is_(None),
                TotpChallenge.expires_at > now,
            )
            .with_for_update()
        )
        challenge = result.first()
        if not challenge or challenge.attempts >= _TOTP_CHALLENGE_MAX_ATTEMPTS:
            raise TotpChallengeExpiredError()

        user = await session.get(User, challenge.user_id)
        totp = await _get_user_totp(session, challenge.user_id)
        if (
            not user
            or user.deleted_at is not None
            or totp is None
            or totp.confirmed_at is None
            or not totp.secret_encrypted
        ):
            raise TotpChallengeExpiredError()

        # Every wrong code of the account in the last hour, on this challenge
        # or an earlier one. Rows out of the window go: nothing reads them
        # any more, and the table stays bounded per user.
        window_start = now - _TOTP_CHALLENGE_WINDOW
        result = await session.exec(
            select(func.sum(TotpChallenge.attempts)).where(
                TotpChallenge.user_id == challenge.user_id,
                TotpChallenge.created_at >= window_start,
            )
        )
        if (result.first() or 0) >= _TOTP_MAX_FAILS_PER_USER_PER_HOUR:
            raise TotpChallengeExpiredError()
        await session.execute(
            sa_delete(TotpChallenge).where(
                TotpChallenge.user_id == challenge.user_id,
                TotpChallenge.created_at < window_start,
            )
        )

        secret = decrypt_secret(totp.secret_encrypted)
        step = matching_step(secret, code, last_used_step=totp.last_used_step)
        if step is None:
            challenge.attempts += 1
            attempts = challenge.attempts
            session.add(challenge)
            # Commit expires the row's attributes, so read the count before.
            await session.commit()
            if attempts >= _TOTP_CHALLENGE_MAX_ATTEMPTS:
                raise TotpChallengeExpiredError()
            raise InvalidTotpCodeError()

        challenge.used_at = now
        session.add(challenge)
        totp.last_used_step = step
        totp.updated_at = now
        if needs_reencryption(totp.secret_encrypted):
            totp.secret_encrypted = encrypt_secret(secret)
        session.add(totp)

        session_token = await _create_session(
            session, user, ip, user_agent, anonymous_user_hash
        )
        await session.commit()

    return session_token
