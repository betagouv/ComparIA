"""ReadinessRegistry — first-class arena state for MCP server health.

Phase 2 of the OAuth refactor. Auth/upstream failure is no longer a runtime
exception that surfaces as a generic "Tool encountered an error" card. Instead,
each server has a tracked ``ServerStatus`` (``READY`` / ``NEEDS_REAUTH`` /
``MISCONFIGURED`` / ``UPSTREAM_DOWN`` / ``UNKNOWN``).

The dispatcher consults ``ReadinessRegistry`` before picking servers; non-READY
servers are excluded from rotation. If fewer than two READY servers exist, the
``/tool-arena/compare`` endpoint returns 503 with a structured body, and the
frontend shows a "tool temporarily unavailable" message instead of two error
cards.

Operators inspect state via ``GET /admin/tool-arena/status``.

Design notes
------------
* Process-local in-memory dict — distributed state is a Phase 3 concern.
* UNKNOWN is treated as NOT ready: the lifespan startup probe runs before
  serving traffic, so the first request sees real state.
* ``last_error`` is exception class name + first 200 chars of repr, scrubbed
  of the most common secret-leakage shapes. Tokens/secrets must never end up
  here — the source exceptions in ``credential.py`` already use ``str(exc)``
  on auth-flow errors that may contain sensitive material in pathological
  cases, so we apply a final defensive truncation here as well.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from backend.tool_arena.config import MCPServerConfig
from backend.tool_arena.credential import (
    CredentialError,
    CredentialMisconfigured,
    CredentialRevoked,
    CredentialUpstreamDown,
    credential_for,
)

logger = logging.getLogger("languia")


# --------------------------------------------------------------------------- #
# Status enum + dataclass
# --------------------------------------------------------------------------- #


class ServerStatus(str, Enum):
    READY = "READY"
    NEEDS_REAUTH = "NEEDS_REAUTH"
    MISCONFIGURED = "MISCONFIGURED"
    UPSTREAM_DOWN = "UPSTREAM_DOWN"
    UNKNOWN = "UNKNOWN"


@dataclass
class ServerReadiness:
    """Snapshot of one server's last-known readiness state."""

    server_id: str
    status: ServerStatus = ServerStatus.UNKNOWN
    last_checked_at: datetime | None = None
    last_error: str | None = None
    consecutive_failures: int = 0

    def to_dict(self) -> dict:
        """JSON-safe representation for the admin endpoint."""
        return {
            "server_id": self.server_id,
            "status": self.status.value,
            "last_checked_at": (
                self.last_checked_at.isoformat()
                if self.last_checked_at is not None
                else None
            ),
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
        }


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #


_MAX_ERROR_LEN = 200


def _scrub_error(exc: BaseException) -> str:
    """Return ``ClassName: <first 200 chars of repr>`` with no secrets.

    We use ``repr`` so the exception class is always visible; truncation caps
    the size to keep admin responses small. The credential module's typed
    errors do not include token bodies in their messages, but defense-in-depth
    matters here.
    """
    cls = type(exc).__name__
    body = repr(exc)
    if len(body) > _MAX_ERROR_LEN:
        body = body[:_MAX_ERROR_LEN] + "...(truncated)"
    return f"{cls}: {body}"


class ReadinessRegistry:
    """Process-local map of ``server_id -> ServerReadiness``.

    All mutations go through ``set_ready`` / ``set_failed`` so
    ``consecutive_failures`` is consistently maintained. Read paths return
    ``UNKNOWN`` for unprobed servers — the dispatcher treats UNKNOWN as not
    ready, which is conservative but matches the lifespan-probe contract.
    """

    def __init__(self) -> None:
        self._state: dict[str, ServerReadiness] = {}

    def get(self, server_id: str) -> ServerReadiness:
        existing = self._state.get(server_id)
        if existing is not None:
            return existing
        return ServerReadiness(server_id=server_id, status=ServerStatus.UNKNOWN)

    def set_ready(self, server_id: str) -> None:
        self._state[server_id] = ServerReadiness(
            server_id=server_id,
            status=ServerStatus.READY,
            last_checked_at=datetime.now(timezone.utc),
            last_error=None,
            consecutive_failures=0,
        )

    def set_failed(
        self,
        server_id: str,
        status: ServerStatus,
        error_message: str | None,
    ) -> None:
        prev = self._state.get(server_id)
        prev_failures = prev.consecutive_failures if prev is not None else 0
        self._state[server_id] = ServerReadiness(
            server_id=server_id,
            status=status,
            last_checked_at=datetime.now(timezone.utc),
            last_error=error_message,
            consecutive_failures=prev_failures + 1,
        )

    def ready_servers(
        self, all_servers: list[MCPServerConfig]
    ) -> list[MCPServerConfig]:
        """Filter the input list to the servers currently in READY state.

        UNKNOWN counts as NOT ready: we want first-probe to gate dispatch so
        the user never hits a server we have not yet validated.
        """
        return [
            s for s in all_servers
            if self.get(s.id).status == ServerStatus.READY
        ]

    def snapshot(self) -> list[ServerReadiness]:
        """Return a list copy of the current state for the admin endpoint."""
        return list(self._state.values())


# Module-level singleton. Mirrors the ``_credential_cache`` / ``_provider_cache``
# pattern in ``credential.py`` and ``auth.py``.
_REGISTRY = ReadinessRegistry()


def get_readiness_registry() -> ReadinessRegistry:
    """Return the process-local ``ReadinessRegistry`` singleton."""
    return _REGISTRY


def _reset_registry_for_tests() -> None:
    """Drop all readiness state. Test isolation only."""
    _REGISTRY._state.clear()


# --------------------------------------------------------------------------- #
# Probe
# --------------------------------------------------------------------------- #


async def _probe_oauth(server: MCPServerConfig) -> None:
    """Run a lightweight OAuth check.

    Reuses ``prewarm_oauth_provider`` so the probe path and the original
    pre-warm path share the same handshake. Failures are translated into
    ``CredentialError`` subclasses by the caller.

    ``prewarm_oauth_provider`` swallows exceptions and returns ``False`` on
    failure, so we re-raise here to map onto the readiness states.
    """
    from backend.tool_arena.auth import prewarm_oauth_provider

    ok = await prewarm_oauth_provider(server)
    if not ok:
        # We do not have the original exception type at this point; treat a
        # failed pre-warm as upstream-down. ``CredentialRevoked`` is reserved
        # for the cases where ``credential_for(...).headers_for(...)`` raises
        # synchronously below.
        raise CredentialUpstreamDown(
            f"OAuth pre-warm failed for {server.id!r}"
        )


async def probe_server(
    server: MCPServerConfig,
    registry: ReadinessRegistry,
    timeout_seconds: float = 10.0,
) -> ServerReadiness:
    """Probe a single MCP server and update the registry.

    For OAuth servers we run the pre-warm handshake (token refresh + MCP
    initialize). For ApiKey/None we validate config presence by calling
    ``headers_for`` once.

    Exception mapping:
        CredentialRevoked        -> NEEDS_REAUTH
        CredentialMisconfigured  -> MISCONFIGURED
        CredentialUpstreamDown   -> UPSTREAM_DOWN
        asyncio.TimeoutError     -> UPSTREAM_DOWN
        Other exceptions         -> UPSTREAM_DOWN (defensive default)
        Success                  -> READY
    """
    cred = credential_for(server)

    async def _run() -> None:
        if server.auth is not None and server.auth.type == "oauth2":
            await _probe_oauth(server)
        else:
            # ApiKey / None: just validate config presence.
            await cred.headers_for(server)

    try:
        await asyncio.wait_for(_run(), timeout=timeout_seconds)
    except CredentialRevoked as exc:
        registry.set_failed(server.id, ServerStatus.NEEDS_REAUTH, _scrub_error(exc))
    except CredentialMisconfigured as exc:
        registry.set_failed(server.id, ServerStatus.MISCONFIGURED, _scrub_error(exc))
    except CredentialUpstreamDown as exc:
        registry.set_failed(server.id, ServerStatus.UPSTREAM_DOWN, _scrub_error(exc))
    except asyncio.TimeoutError as exc:
        registry.set_failed(server.id, ServerStatus.UPSTREAM_DOWN, _scrub_error(exc))
    except CredentialError as exc:
        # Catch-all for any subclass we did not enumerate above.
        registry.set_failed(server.id, ServerStatus.UPSTREAM_DOWN, _scrub_error(exc))
    except Exception as exc:  # noqa: BLE001 — keep loop alive
        logger.warning(
            "probe_server: unexpected error for %s: %s: %s",
            server.id, type(exc).__name__, exc,
        )
        registry.set_failed(server.id, ServerStatus.UPSTREAM_DOWN, _scrub_error(exc))
    else:
        registry.set_ready(server.id)

    return registry.get(server.id)


# --------------------------------------------------------------------------- #
# Background loop
# --------------------------------------------------------------------------- #


async def readiness_probe_loop(
    servers: list[MCPServerConfig],
    interval_seconds: int = 60,
) -> None:
    """Periodically probe every server. Runs until cancelled.

    Wrapped in a broad except so a transient failure in one iteration does not
    kill the loop.
    """
    if not servers:
        logger.info("readiness_probe_loop: no servers to probe; loop exits.")
        return

    registry = get_readiness_registry()
    logger.info(
        "readiness_probe_loop: started (interval=%ds, servers=%s)",
        interval_seconds, [s.id for s in servers],
    )
    try:
        while True:
            try:
                await asyncio.gather(
                    *(probe_server(s, registry) for s in servers),
                    return_exceptions=True,
                )
            except Exception as exc:  # noqa: BLE001 — keep loop alive
                logger.error(
                    "readiness_probe_loop: probe iteration failed: %s: %s",
                    type(exc).__name__, exc,
                )
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        logger.info("readiness_probe_loop: cancelled, exiting cleanly.")
        raise


def get_probe_interval_seconds() -> int:
    """Read ``READINESS_PROBE_INTERVAL`` env var; default 60s."""
    raw = os.environ.get("READINESS_PROBE_INTERVAL", "60")
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "READINESS_PROBE_INTERVAL=%r is not an int; falling back to 60", raw,
        )
        return 60
    return max(value, 1)
