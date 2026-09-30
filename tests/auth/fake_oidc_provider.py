"""
A fake OpenID Provider for the OIDC tests.

It serves the discovery, token and userinfo endpoints from an
`httpx.MockTransport`, and `serving` swaps it in for the client that
`backend.auth.oidc` builds for every call to the provider. The real discovery
and code exchange code runs; only the network is faked.
"""

import base64
import contextlib
import json
import time

import httpx

import backend.auth.oidc as oidc
from utils.secrets import encrypt_secret

ISSUER = "https://idp.example.test"
CLIENT_ID = "client-123"
CLIENT_SECRET = "super-secret"
# What the settings row holds for the secret above.
ENCRYPTED_CLIENT_SECRET = encrypt_secret(CLIENT_SECRET).encode()


def fake_jwt(payload: dict) -> str:
    """A compact JWT with a real header and payload and a throwaway signature:
    signatures are never verified."""

    def segment(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{segment({'alg': 'RS256'})}.{segment(payload)}.fake-signature"


class FakeProvider:
    """A provider that signs in `agent@example.com` unless a test says
    otherwise. Tweak an attribute to change what an endpoint answers; the
    requests it received are kept in `requests`."""

    def __init__(self):
        self.discovery: dict | None = {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/authorize",
            "token_endpoint": f"{ISSUER}/token",
            "userinfo_endpoint": f"{ISSUER}/userinfo",
        }
        # Claims of the id_token; `nonce` is what the callback checks against
        # the one stored at initiation.
        self.id_token_claims: dict = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": "user-1",
            "nonce": "the-nonce",
            "exp": int(time.time()) + 3600,
        }
        self.userinfo_claims: dict = {
            "sub": "user-1",
            "email": "agent@example.com",
            "email_verified": True,
        }
        self.userinfo_as_jwt = False
        # Overrides of the token response, when a test needs a broken one.
        self.token_status = 200
        self.token_body: dict | None = None
        self.unreachable = False
        self.requests: list[httpx.Request] = []

    def requests_to(self, path: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == path]

    def _token_body(self) -> dict:
        if self.token_body is not None:
            return self.token_body
        return {
            "access_token": "access-token",
            "token_type": "Bearer",
            "id_token": fake_jwt(self.id_token_claims),
        }

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.unreachable:
            raise httpx.ConnectError("provider unreachable", request=request)
        path = request.url.path
        if path == "/.well-known/openid-configuration":
            if self.discovery is None:
                return httpx.Response(404)
            return httpx.Response(200, json=self.discovery)
        if path == "/token":
            return httpx.Response(self.token_status, json=self._token_body())
        if path == "/userinfo":
            if self.userinfo_as_jwt:
                return httpx.Response(
                    200,
                    text=fake_jwt(self.userinfo_claims),
                    headers={"content-type": "application/jwt"},
                )
            return httpx.Response(200, json=self.userinfo_claims)
        return httpx.Response(404)


@contextlib.contextmanager
def serving(provider: FakeProvider):
    """Route every call `backend.auth.oidc` makes to `provider`."""

    def http_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(provider.handle))

    original = oidc._http_client
    oidc._http_client = http_client
    # Discovery documents are cached per issuer: a previous test's must not
    # answer for this provider.
    oidc.discover_provider.cache_clear()
    try:
        yield provider
    finally:
        oidc._http_client = original
        oidc.discover_provider.cache_clear()
