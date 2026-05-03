"""Credential Module — single dispatch seam for MCP server auth.

Phase 1 of the OAuth refactor: collapse per-call auth-type branching in
``client.py`` into a small Adapter family behind a uniform ``Credential``
Protocol. ``client.py`` no longer asks "what kind of auth is this?" — it just
asks the credential for the right HTTP headers and (for OAuth) hands the SDK
the existing ``OAuthClientProvider`` instance.

Known asymmetry — OAuth and the MCP SDK
---------------------------------------
The MCP SDK's ``streamablehttp_client(..., auth=provider)`` integration runs
the OAuth flow internally: it intercepts 401s, refreshes via the provider's
token storage, and rewrites the ``Authorization`` header on retry. The
provider does not expose a public "give me a fresh access_token now" method —
the only clean way to drive the refresh dance is to actually open a session.

We deliberately do NOT pre-fetch a Bearer header for OAuth here, because:

* Calling ``async_auth_flow`` outside an HTTP request is awkward and bypasses
  the SDK's 401-retry contract.
* If we returned a header from a pre-warmed token, an expiry between
  ``headers_for`` and the actual MCP request would still 401, and the SDK's
  retry path is the supported recovery mechanism.

So ``OAuth2Credential.headers_for`` returns ``{}`` and exposes the existing
``CompaRAGOAuthProvider`` via ``provider_for(server)``. ``client.py`` keeps
passing ``auth=provider`` to ``streamablehttp_client`` for OAuth servers.
Phase 2 may revisit this once we add explicit readiness state and can
short-circuit calls when the provider has no usable refresh token.

What this module *does* normalize today:

* Auth-type dispatch lives in one place (``credential_for``).
* Per-server caching mirrors the ``_provider_cache`` in ``auth.py``.
* Errors from the OAuth provider are translated into a small typed hierarchy
  (``CredentialRevoked`` / ``CredentialMisconfigured`` / ``CredentialUpstreamDown``)
  so callers can act on intent rather than provider-internal exception types.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

import httpx
from mcp.client.auth.exceptions import OAuthTokenError

from backend.tool_arena.config import MCPServerConfig

logger = logging.getLogger("languia")


# --------------------------------------------------------------------------- #
# Typed errors
# --------------------------------------------------------------------------- #


class CredentialError(Exception):
    """Base class for credential acquisition failures."""


class CredentialRevoked(CredentialError):
    """Refresh token rejected / interactive OAuth flow required.

    Raised when the upstream identity provider has invalidated our refresh
    token (rotation race, manual revocation, expired offline grant) or when
    the SDK tries to fall back to the authorization-code redirect flow on a
    headless server. Recovery: re-run ``scripts/auth_setup.py`` (Phase 3 will
    expose this as an admin endpoint).
    """


class CredentialMisconfigured(CredentialError):
    """Configuration error: missing env var, malformed config, etc.

    Raised when the credential cannot even be constructed — e.g. the
    ``client_secret_env`` env var is unset and no client_info is stored, or
    an api-key server's ``key_env`` is unset.
    """


class CredentialUpstreamDown(CredentialError):
    """Token endpoint unreachable or returning 5xx / timeouts."""


# --------------------------------------------------------------------------- #
# Protocol
# --------------------------------------------------------------------------- #


@runtime_checkable
class Credential(Protocol):
    """Uniform interface for obtaining MCP request auth headers.

    Implementations must be cheap to call repeatedly — the per-server cache
    in ``credential_for`` ensures only one instance exists per server id.
    """

    async def headers_for(self, server: MCPServerConfig) -> dict[str, str]:
        """Return HTTP headers to attach to the MCP request.

        For OAuth servers the SDK's ``auth=provider`` integration is the
        authoritative path — see module docstring. ``OAuth2Credential``
        returns ``{}`` here and exposes the provider separately.

        Raises:
            CredentialMisconfigured: Config inputs missing.
            CredentialRevoked: OAuth tokens unrecoverably rejected.
            CredentialUpstreamDown: Token endpoint unreachable.
        """
        ...


# --------------------------------------------------------------------------- #
# Adapters
# --------------------------------------------------------------------------- #


class NoneCredential:
    """No-auth servers: emit no headers, never fail."""

    async def headers_for(self, server: MCPServerConfig) -> dict[str, str]:
        return {}


class ApiKeyCredential:
    """Static API key from an env var.

    Honours the existing ``ApiKeyAuth`` shape (``key_env`` + ``header``) so
    behaviour is byte-identical to the inline branch in ``client.py``
    pre-refactor.
    """

    async def headers_for(self, server: MCPServerConfig) -> dict[str, str]:
        auth = server.auth
        if auth is None or auth.type != "api_key":
            raise CredentialMisconfigured(
                f"ApiKeyCredential used on server {server.id!r} with auth={auth!r}"
            )
        key = os.environ.get(auth.key_env, "")
        if not key:
            raise CredentialMisconfigured(
                f"API key env var {auth.key_env!r} is unset for server {server.id!r}"
            )
        return {auth.header: key}


class OAuth2Credential:
    """OAuth2 wrapper around ``CompaRAGOAuthProvider``.

    See module docstring for why ``headers_for`` returns ``{}``. Use
    ``provider_for`` to obtain the SDK provider that ``client.py`` should
    pass as ``auth=`` to ``streamablehttp_client``.
    """

    async def headers_for(self, server: MCPServerConfig) -> dict[str, str]:
        # Surface obvious misconfiguration eagerly so the caller can short-
        # circuit before opening a transport. Note: an empty env var does NOT
        # always mean the credential is unusable — `auth.py` may fall back to
        # stored client_info. We only hard-fail when *both* sources are
        # absent, mirroring the warning in `build_oauth_provider`.
        auth = server.auth
        if auth is None or auth.type != "oauth2":
            raise CredentialMisconfigured(
                f"OAuth2Credential used on server {server.id!r} with auth={auth!r}"
            )

        try:
            # Touching the provider validates that we *can* construct one;
            # the heavy lifting (refresh, 401 retry) happens later inside
            # the SDK's auth flow when client.py opens streamablehttp_client.
            self.provider_for(server)
        except CredentialError:
            raise
        except OAuthTokenError as exc:
            raise CredentialRevoked(str(exc)) from exc
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise CredentialUpstreamDown(str(exc)) from exc
        except RuntimeError as exc:
            # _redirect_handler / _callback_handler raise RuntimeError when
            # the SDK falls back to interactive auth on a headless server.
            raise CredentialRevoked(str(exc)) from exc

        return {}

    def provider_for(self, server: MCPServerConfig):
        """Return the cached ``CompaRAGOAuthProvider`` for this server.

        Errors from the underlying provider construction are translated into
        the credential error hierarchy.
        """
        # Local import keeps this module importable even when the OAuth code
        # path is not exercised (tests, none-auth-only deployments).
        from backend.tool_arena.auth import get_oauth_provider

        try:
            return get_oauth_provider(server)
        except KeyError as exc:
            raise CredentialMisconfigured(
                f"Missing config key for OAuth server {server.id!r}: {exc}"
            ) from exc
        except OAuthTokenError as exc:
            raise CredentialRevoked(str(exc)) from exc
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise CredentialUpstreamDown(str(exc)) from exc
        except RuntimeError as exc:
            raise CredentialRevoked(str(exc)) from exc


# --------------------------------------------------------------------------- #
# Factory + cache
# --------------------------------------------------------------------------- #


_credential_cache: dict[str, Credential] = {}


def credential_for(server: MCPServerConfig) -> Credential:
    """Return a cached ``Credential`` for the given server.

    Cache key is ``server.id`` — mirrors ``_OAUTH_PROVIDERS`` style cache in
    ``auth.py``. Tests can clear via ``_clear_credential_cache``.
    """
    cached = _credential_cache.get(server.id)
    if cached is not None:
        return cached

    auth = server.auth
    cred: Credential
    if auth is None or auth.type == "none":
        cred = NoneCredential()
    elif auth.type == "api_key":
        cred = ApiKeyCredential()
    elif auth.type == "oauth2":
        cred = OAuth2Credential()
    else:  # pragma: no cover — pydantic discriminator prevents this
        raise CredentialMisconfigured(
            f"Unknown auth type {auth.type!r} on server {server.id!r}"
        )

    _credential_cache[server.id] = cred
    return cred


def _clear_credential_cache() -> None:
    """Clear the per-server credential cache. For test isolation only."""
    _credential_cache.clear()


def _invalidate_cache(server_id: str) -> None:
    """Drop the cached ``Credential`` for one server.

    Called by the admin re-key endpoint so the next call to ``credential_for``
    constructs a fresh adapter that observes the newly-seeded tokens.
    """
    _credential_cache.pop(server_id, None)
