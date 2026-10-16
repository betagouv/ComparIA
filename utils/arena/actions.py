import logging
import math
from uuid import UUID

from backend.arena import limits

logger = logging.getLogger("comparia.arena")


def _identities(session: str | None, ip: str | None, user: UUID | None) -> list[str]:
    identities = []
    if session:
        identities.append(limits.session_identity(session))
    if user:
        identities.append(limits.account_identity(user))
    if ip:
        identities.append(limits.network_identity(ip))
    if not identities:
        logger.error("Give --session, --user, --ip, or several.")
        raise SystemExit(1)
    return identities


def _resets(allowance: limits.Allowance) -> str:
    if allowance.resets_in is not None:
        return f"resets in {math.ceil(allowance.resets_in / 60)} min"
    # No expiry: a counter is there but Redis will never drop it.
    return "never resets" if allowance.used else "nothing counted"


async def limits_show(
    *, session: str | None = None, ip: str | None = None, user: UUID | None = None
) -> None:
    """
    Show what a session, an account or an IP spent of each allowance, and
    when it resets.

    Args:
        session: Anonymous session hash, as stored on its comparisons
        ip: Caller IP. An IPv6 address counts for its whole /64
        user: Account id, which counts instead of the session while signed in
    """
    # The limits an admin set, rather than the env defaults.
    await limits.load_settings()
    for allowance in limits.read_counters(_identities(session, ip, user)).allowances:
        logger.info(
            f"{allowance.identity} {allowance.pool}: "
            f"{limits.counted(allowance.pool, allowance.used)} of "
            f"{limits.counted(allowance.pool, allowance.limit)}, {_resets(allowance)}"
            f"{', spent' if allowance.spent else ''}"
        )


def limits_reset(
    *, session: str | None = None, ip: str | None = None, user: UUID | None = None
) -> None:
    """
    Give a session, an account or an IP its whole allowances back.

    Args:
        session: Anonymous session hash, as stored on its comparisons
        ip: Caller IP. An IPv6 address counts for its whole /64
        user: Account id, which counts instead of the session while signed in
    """
    deleted = limits.reset_counters(_identities(session, ip, user))
    logger.info(f"Reset {deleted} counters")
