"""
OIDC authorization-code flow mechanics.

Only this module talks to the identity provider. The router imports
`discover_provider` and `exchange_code_for_claims` by name and patches them
in tests the same way the email flow patches `request_login_code` /
`send_login_code`.
"""

import base64
import json
import logging
import secrets
from dataclasses import asdict, dataclass
from typing import cast
from urllib.parse import urlencode

import httpx
from async_lru import alru_cache

from backend.config import settings
from utils.storage.redis import REDIS_OIDC_STATE_PREFIX, get_redis_client

logger = logging.getLogger("languia")

# Window short enough that a leaked state can't be replayed much later, long
# enough to cover a user reading their provider's consent screen.
OIDC_STATE_TTL_SECONDS = 600

# Discovery documents change rarely; caching them saves a round trip to the
# provider on each leg of a sign-in. Short enough that a provider-side change,
# or an issuer edited in the admin panel, is picked up without a restart.
_DISCOVERY_TTL_SECONDS = 600

_DISCOVERY_PATH = "/.well-known/openid-configuration"


class OIDCProviderError(Exception):
    """The provider answered, but not with something we can trust."""


@dataclass
class PendingLogin:
    """What `oidc_login` remembers about a sign-in until its callback."""

    nonce: str
    redirect: str
    merge: bool


def discovery_url(issuer: str) -> str:
    """Build the `.well-known/openid-configuration` URL for an issuer.

    Issuers are configured without trailing slash in practice; rstrip handles
    the ones that aren't. The path is appended rather than urljoined because a
    bare issuer is an origin, not a URL with a path to resolve against.
    """
    return issuer.rstrip("/") + _DISCOVERY_PATH


def _same_issuer(a: object, b: object) -> bool:
    return isinstance(a, str) and isinstance(b, str) and a.rstrip("/") == b.rstrip("/")


def validate_discovery(document: dict, issuer: str) -> dict:
    """Refuse a discovery document published for another issuer (OIDC
    Discovery 4.3): the endpoints it lists are not the configured provider's."""
    if not _same_issuer(document.get("issuer"), issuer):
        raise OIDCProviderError(
            f"discovery issuer {document.get('issuer')!r} does not match {issuer!r}"
        )
    return document


@alru_cache(maxsize=4, ttl=_DISCOVERY_TTL_SECONDS)
async def discover_provider(issuer: str) -> dict:
    """Fetch the provider's discovery document.

    This is the single network seam: tests patch this name in `auth_router`
    so no test ever reaches a real identity provider.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(discovery_url(issuer))
        response.raise_for_status()
        return validate_discovery(response.json(), issuer)


def issue_state(*, redirect: str, merge: bool) -> tuple[str, str]:
    """Generate a fresh `state`/`nonce` pair and store it in Redis, along with
    where to send the user afterwards.

    The callback reads and deletes the key: a state that's missing on lookup
    is either expired or already used, both of which reject the callback. This
    mirrors the NX-write-then-expire anti-replay in `backend/arena/captcha.py`.
    """
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    pending = PendingLogin(nonce=nonce, redirect=redirect, merge=merge)
    try:
        stored = get_redis_client().set(
            REDIS_OIDC_STATE_PREFIX + state,
            json.dumps(asdict(pending)),
            ex=OIDC_STATE_TTL_SECONDS,
            nx=True,
        )
    except Exception as e:
        logger.error(f"[OIDC] failed to store state: {e}")
        raise
    if not stored:
        # A collision on a 32-byte token is not a real failure mode; surface it
        # loudly rather than issue a duplicate state.
        raise RuntimeError("OIDC state collision, retry the request")
    return state, nonce


def oidc_callback_url() -> str:
    """Public URL of the callback endpoint, as advertised to the provider.

    Every backend route is mounted under `/api` (see `backend/main.py`), so the
    path the provider redirects to carries that prefix — the bare `/auth/...`
    path is a frontend route and 404s. The origin is the backend's own
    (`COMPARIA_API_URL`, falling back to the app origin), because in dev the
    backend does not share a host with the frontend.
    """
    return f"{settings.api_origin}/api/auth/oidc/callback"


def build_authorization_url(
    *,
    authorization_endpoint: str,
    client_id: str,
    scopes: list[str],
    redirect: str = "/",
    merge: bool = False,
) -> tuple[str, str]:
    """Build the authorization endpoint URL with a fresh `state`/`nonce`.

    Returns the URL and the state, which the router also hands to the browser
    so the callback can check it comes back to the one that started.
    """
    state, nonce = issue_state(redirect=redirect, merge=merge)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": oidc_callback_url(),
        "scope": " ".join(scopes),
        "state": state,
        "nonce": nonce,
    }
    return f"{authorization_endpoint}?{urlencode(params)}", state


def consume_state(state: str) -> PendingLogin | None:
    """Read and atomically delete what was stored for this `state`.

    Returns None when the state was never issued, already used, or expired —
    every one of which rejects the callback. Single use is what makes the
    state a replay defense, mirroring the Altcha anti-replay pattern in
    `backend/arena/captcha.py`.
    """
    client = get_redis_client()
    # The client is built with decode_responses=True, so this is a str.
    raw = cast("str | None", client.getdel(REDIS_OIDC_STATE_PREFIX + state))
    if raw is None:
        return None
    try:
        return PendingLogin(**json.loads(raw))
    except (TypeError, ValueError):
        logger.warning("[OIDC] unreadable pending login in Redis")
        return None


async def exchange_code_for_claims(
    *,
    token_endpoint: str,
    userinfo_endpoint: str,
    issuer: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    """Exchange the authorization code for tokens and retrieve userinfo claims.

    The single network seam in the callback flow: tests patch this name in
    `auth_router` so no test ever reaches a real identity provider. Returns the
    userinfo claims plus the `nonce` claim read from the id_token, so the
    router can validate it against the stored nonce. The id_token and
    access_token are discarded as soon as this function returns: ComparIA
    keeps no provider-side session, no refresh, no persisted token.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        token_response = await client.post(
            token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            headers={"Accept": "application/json"},
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data["access_token"]
        id_token = token_data.get("id_token")
        if not id_token:
            raise OIDCProviderError("token response has no id_token")
        id_claims = validate_id_token(id_token, issuer=issuer, client_id=client_id)

        userinfo_response = await client.get(
            userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_response.raise_for_status()
        content_type = userinfo_response.headers.get("content-type", "")
        # A provider configured for a signed userinfo response (ProConnect's
        # default: "Algorithme de signature user-info: RS256") returns a
        # compact JWT (`application/jwt`) instead of a plain JSON object; a
        # provider left unsigned returns JSON directly. Same trust model as
        # the id_token either way: no JWKS verification, the response arrives
        # over a direct TLS call to an endpoint the discovery document
        # already pointed us at.
        if "application/jwt" in content_type:
            claims = _decode_jwt_payload(userinfo_response.text)
        else:
            claims = userinfo_response.json()

    return merge_userinfo_claims(claims, id_claims)


def merge_userinfo_claims(userinfo: dict, id_claims: dict) -> dict:
    """Attach the id_token nonce to the userinfo claims, once they are known
    to be about the same person: OIDC Core 5.3.2 forbids using userinfo whose
    `sub` differs from the id_token's."""
    if not id_claims.get("sub") or userinfo.get("sub") != id_claims.get("sub"):
        raise OIDCProviderError("userinfo sub does not match the id_token sub")
    return {**userinfo, "nonce": id_claims.get("nonce")}


def validate_id_token(id_token: str, *, issuer: str, client_id: str) -> dict:
    """Check the id_token was issued by our provider, for us (OIDC Core 3.1.3.7).

    The signature is not verified: the token comes straight from the token
    endpoint over TLS, which the spec accepts in place of it. `iss` and `aud`
    still have to be ours.
    """
    try:
        claims = _decode_jwt_payload(id_token)
    except Exception as e:
        raise OIDCProviderError(f"unreadable id_token: {e}") from e
    if not _same_issuer(claims.get("iss"), issuer):
        raise OIDCProviderError(f"id_token iss {claims.get('iss')!r} is not ours")
    audience = claims.get("aud")
    audiences = audience if isinstance(audience, list) else [audience]
    if client_id not in audiences:
        raise OIDCProviderError("id_token was not issued for this client")
    return claims


def _decode_jwt_payload(token: str) -> dict:
    """Decode a compact JWT's payload without verifying its signature.

    Signature verification is intentionally out of scope (see
    `validate_id_token`): every JWT handled here arrives over a direct TLS
    call to an endpoint the discovery document already pointed us at, not
    from the browser.
    """
    _header, payload_b64, _signature = token.split(".")
    padding = "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64 + padding))
