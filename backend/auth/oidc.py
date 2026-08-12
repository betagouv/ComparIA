"""
OIDC authorization-code flow mechanics.

Only this module talks to the identity provider. The router imports
`discover_provider` by name and patches it in tests the same way the email
flow patches `request_login_code` / `send_login_code`.
"""

import logging
import secrets
from urllib.parse import urlencode

import httpx

from backend.config import settings
from utils.storage.redis import REDIS_OIDC_STATE_PREFIX, get_redis_client

logger = logging.getLogger("languia")

# Window short enough that a leaked state can't be replayed much later, long
# enough to cover a user reading their provider's consent screen.
OIDC_STATE_TTL_SECONDS = 600

_DISCOVERY_PATH = "/.well-known/openid-configuration"


def discovery_url(issuer: str) -> str:
    """Build the `.well-known/openid-configuration` URL for an issuer.

    Issuers are configured without trailing slash in practice; rstrip handles
    the ones that aren't. The path is appended rather than urljoined because a
    bare issuer is an origin, not a URL with a path to resolve against.
    """
    return issuer.rstrip("/") + _DISCOVERY_PATH


async def discover_provider(issuer: str) -> dict:
    """Fetch the provider's discovery document.

    This is the single network seam: tests patch this name in `auth_router`
    so no test ever reaches a real identity provider.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(discovery_url(issuer))
        response.raise_for_status()
        return response.json()


def issue_state_and_nonce() -> tuple[str, str]:
    """Generate a fresh `state`/`nonce` pair and store it in Redis.

    The callback reads and deletes the key: a state that's missing on lookup
    is either expired or already used, both of which reject the callback. This
    mirrors the NX-write-then-expire anti-replay in `backend/arena/captcha.py`.
    """
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    try:
        stored = get_redis_client().set(
            REDIS_OIDC_STATE_PREFIX + state,
            nonce,
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
    """Public URL of the callback endpoint, as advertised to the provider."""
    return f"{settings.COMPARIA_APP_URL}/auth/oidc/callback"


def build_authorization_url(
    *, authorization_endpoint: str, client_id: str, scopes: list[str]
) -> str:
    """Build the authorization endpoint URL with a fresh `state`/`nonce`."""
    state, nonce = issue_state_and_nonce()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": oidc_callback_url(),
        "scope": " ".join(scopes),
        "state": state,
        "nonce": nonce,
    }
    return f"{authorization_endpoint}?{urlencode(params)}"
