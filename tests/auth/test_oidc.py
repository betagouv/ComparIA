"""
Tests for the pure JWT-payload-decoding helpers in `backend/auth/oidc.py`
(no DB, no Redis, no real identity provider, no network).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc.py
"""

import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
os.environ.setdefault("OIDC_ENCRYPTION_KEY", "aa" * 32)

from backend.auth.oidc import _decode_jwt_payload, _id_token_nonce  # noqa: E402


def _fake_jwt(payload: dict) -> str:
    """A compact JWT with a real header/payload and a throwaway signature —
    good enough to exercise decoding, since signatures are never verified."""

    def segment(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{segment({'alg': 'RS256'})}.{segment(payload)}.fake-signature"


def test_decode_jwt_payload_reads_the_claims():
    token = _fake_jwt({"email": "agent@example.test", "nonce": "the-nonce"})
    assert _decode_jwt_payload(token) == {
        "email": "agent@example.test",
        "nonce": "the-nonce",
    }


def test_decode_jwt_payload_handles_unpadded_base64url():
    # Real JWTs commonly need padding restored; a payload length that isn't
    # a multiple of 4 base64 chars exercises that path.
    token = _fake_jwt({"a": "x"})
    assert _decode_jwt_payload(token)["a"] == "x"


def test_id_token_nonce_reads_the_nonce_claim():
    token = _fake_jwt({"sub": "user-1", "nonce": "abc123"})
    assert _id_token_nonce(token) == "abc123"


def test_id_token_nonce_returns_none_on_a_malformed_token():
    assert _id_token_nonce("not-a-jwt") is None


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
