import base64

from cryptography.fernet import Fernet

from backend.config import settings


def _fernet() -> Fernet:
    key_hex = settings.OIDC_ENCRYPTION_KEY
    if not key_hex:
        raise RuntimeError(
            "OIDC_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    try:
        raw = bytes.fromhex(key_hex)
    except ValueError as exc:
        raise RuntimeError("OIDC_ENCRYPTION_KEY must be a 64-character hex string") from exc
    if len(raw) != 32:
        raise RuntimeError(
            "OIDC_ENCRYPTION_KEY must be exactly 64 hex characters (32 bytes), "
            f"got {len(raw) * 2}"
        )
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_oidc_secret(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt_oidc_secret(ciphertext: bytes) -> str:
    return _fernet().decrypt(ciphertext).decode()
