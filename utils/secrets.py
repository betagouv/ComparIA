"""Secrets at rest.

Anything secret that lives in the database goes through here, encrypted with
`COMPARIA_ENCRYPTION_KEY`. The setting takes several keys, comma-separated:
the first encrypts, every one decrypts, so a key can be rotated by adding the
new one in front and dropping the old one once every row has been rewritten.
"""

import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from backend.config import settings

logger = logging.getLogger("languia")


class SecretUnreadableError(Exception):
    """A stored secret that no configured key opens. The secret exists, so
    the caller must not read this as a missing one, nor as a wrong input."""

    def __init__(
        self,
        message: str = "a stored secret cannot be decrypted with the configured keys",
    ) -> None:
        super().__init__(message)


def _keys() -> list[str]:
    return [k.strip() for k in settings.COMPARIA_ENCRYPTION_KEY.split(",") if k.strip()]


@lru_cache
def _fernet() -> MultiFernet:
    # Every key was checked when backend.config loaded, so a bad one cannot
    # reach here.
    return MultiFernet([Fernet(k) for k in _keys()])


def encrypt_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Raises SecretUnreadableError when no configured key opens the token,
    which is logged: it means a key was dropped too early, not that there
    was no secret."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        logger.error(
            "[SECRETS] a stored secret cannot be decrypted with the current keys"
        )
        raise SecretUnreadableError()


def needs_reencryption(token: str) -> bool:
    """True when the token was made with an older key of the list."""
    keys = _keys()
    if len(keys) < 2:
        return False
    try:
        Fernet(keys[0]).decrypt(token.encode())
        return False
    except InvalidToken:
        return True
