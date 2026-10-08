"""
Tests for the pure helpers in `backend/auth/oidc.py`: JWT decoding, id_token,
userinfo and discovery checks, pending-login storage (no DB, no Redis, no
real identity provider, no network).

Run with pytest, or directly:
    uv run python tests/auth/test_oidc.py
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import backend.auth.oidc as oidc  # noqa: E402
from backend.auth.oidc import (  # noqa: E402
    OIDCProviderError,
    PendingLogin,
    _decode_jwt_payload,
    email_explicitly_unverified,
    merge_userinfo_claims,
    oidc_available,
    validate_discovery,
    validate_id_token,
)
from tests.auth.fake_oidc_provider import ENCRYPTED_CLIENT_SECRET  # noqa: E402

ISSUER = "https://idp.example.test"
CLIENT_ID = "client-123"


def raises(exception, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except exception:
        return
    raise AssertionError(f"{fn.__name__} did not raise {exception.__name__}")


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


def _id_token(**claims):
    return _fake_jwt(
        {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "user-1",
            "exp": int(time.time()) + 3600,
            **claims,
        }
    )


def test_validate_id_token_returns_the_claims_of_a_token_issued_for_us():
    claims = validate_id_token(
        _id_token(nonce="abc123"), issuer=ISSUER, client_id=CLIENT_ID
    )
    assert claims["nonce"] == "abc123"


def test_validate_id_token_accepts_an_audience_list_and_a_trailing_slash():
    token = _id_token(iss=ISSUER + "/", aud=["other", CLIENT_ID])
    assert validate_id_token(token, issuer=ISSUER, client_id=CLIENT_ID)


def test_validate_id_token_rejects_another_issuer():
    token = _id_token(iss="https://elsewhere.test")
    raises(
        OIDCProviderError, validate_id_token, token, issuer=ISSUER, client_id=CLIENT_ID
    )


def test_validate_id_token_rejects_a_token_for_another_client():
    token = _id_token(aud="someone-else")
    raises(
        OIDCProviderError, validate_id_token, token, issuer=ISSUER, client_id=CLIENT_ID
    )


def test_validate_id_token_rejects_an_expired_token():
    token = _id_token(exp=int(time.time()) - 3600)
    raises(
        OIDCProviderError, validate_id_token, token, issuer=ISSUER, client_id=CLIENT_ID
    )


def test_validate_id_token_allows_a_small_clock_skew():
    token = _id_token(exp=int(time.time()) - 10)
    assert validate_id_token(token, issuer=ISSUER, client_id=CLIENT_ID)


def test_validate_id_token_rejects_a_missing_or_unreadable_expiry():
    for exp in (None, "soon", True):
        token = _id_token(exp=exp)
        raises(
            OIDCProviderError,
            validate_id_token,
            token,
            issuer=ISSUER,
            client_id=CLIENT_ID,
        )


def test_email_explicitly_unverified_reads_booleans_and_strings():
    for value in (False, "false", "False", " FALSE "):
        assert email_explicitly_unverified({"email_verified": value}), value
    for value in (True, "true", "TRUE"):
        assert not email_explicitly_unverified({"email_verified": value}), value


def test_email_explicitly_unverified_treats_anything_else_as_absent():
    assert not email_explicitly_unverified({})
    assert not email_explicitly_unverified({"email_verified": None})
    assert not email_explicitly_unverified({"email_verified": "maybe"})


def test_validate_id_token_rejects_a_malformed_token():
    raises(
        OIDCProviderError,
        validate_id_token,
        "not-a-jwt",
        issuer=ISSUER,
        client_id=CLIENT_ID,
    )


def test_merge_userinfo_claims_adds_the_id_token_nonce():
    claims = merge_userinfo_claims(
        {"sub": "user-1", "email": "agent@example.com"},
        {"sub": "user-1", "nonce": "abc123"},
    )
    assert claims == {"sub": "user-1", "email": "agent@example.com", "nonce": "abc123"}


def test_merge_userinfo_claims_rejects_userinfo_about_someone_else():
    raises(
        OIDCProviderError,
        merge_userinfo_claims,
        {"sub": "user-2", "email": "boss@example.com"},
        {"sub": "user-1", "nonce": "abc123"},
    )


def test_merge_userinfo_claims_rejects_userinfo_without_a_subject():
    raises(
        OIDCProviderError,
        merge_userinfo_claims,
        {"email": "boss@example.com"},
        {"nonce": "abc123"},
    )


def test_validate_discovery_accepts_the_configured_issuer():
    document = {"issuer": ISSUER + "/", "token_endpoint": ISSUER + "/token"}
    assert validate_discovery(document, ISSUER) is document


def test_validate_discovery_rejects_a_document_for_another_issuer():
    raises(
        OIDCProviderError,
        validate_discovery,
        {"issuer": "https://elsewhere.test"},
        ISSUER,
    )


def _config(**overrides):
    fields = dict(
        auth_methods=["email_code", "oidc"],
        oidc_issuer=ISSUER,
        oidc_client_id=CLIENT_ID,
        oidc_client_secret_encrypted=ENCRYPTED_CLIENT_SECRET,
        oidc_scopes=["openid", "email"],
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def test_oidc_is_available_with_the_method_enabled_and_a_readable_config():
    assert oidc_available(_config())


def test_oidc_is_unavailable_unless_the_method_is_enabled():
    assert not oidc_available(_config(auth_methods=["email_code"]))


def test_oidc_is_unavailable_with_an_incomplete_provider_config():
    for missing in (
        dict(oidc_issuer=None),
        dict(oidc_client_id=None),
        dict(oidc_client_secret_encrypted=None),
        dict(oidc_scopes=["email"]),
    ):
        assert not oidc_available(_config(**missing)), missing


def test_oidc_is_unavailable_when_the_client_secret_cannot_be_read():
    assert not oidc_available(_config(oidc_client_secret_encrypted=b"not-a-token"))


class FakeRedis:
    def __init__(self):
        self.store = {}

    def set(self, key, value, ex=None, nx=False):
        self.store[key] = value
        return True

    def getdel(self, key):
        return self.store.pop(key, None)


def test_a_pending_login_is_read_back_once():
    fake = FakeRedis()
    original = oidc.get_redis_client
    oidc.get_redis_client = lambda: fake
    try:
        state, nonce = oidc.issue_state(redirect="/arena", merge=True)
        assert oidc.consume_state(state) == PendingLogin(
            nonce=nonce, redirect="/arena", merge=True
        )
        assert oidc.consume_state(state) is None
    finally:
        oidc.get_redis_client = original


if __name__ == "__main__":
    for name, fn in sorted(dict(globals()).items()):
        if name.startswith("test_"):
            fn()
            print(f"ok {name}")
