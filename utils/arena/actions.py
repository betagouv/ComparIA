import logging
import math

from backend.arena import limits

logger = logging.getLogger("comparia.arena")


def _identities(session: str | None, ip: str | None) -> list[str]:
    identities = []
    if session:
        identities.append(limits.session_identity(session))
    if ip:
        identities.append(limits.ip_identity(ip))
    if not identities:
        logger.error("Give --session, --ip or both.")
        raise SystemExit(1)
    return identities


def _resets(allowance: limits.Allowance) -> str:
    if allowance.resets_in is not None:
        return f"resets in {math.ceil(allowance.resets_in / 60)} min"
    # No expiry: a counter is there but Redis will never drop it.
    return "never resets" if allowance.used else "nothing counted"


def limits_show(*, session: str | None = None, ip: str | None = None) -> None:
    """
    Show what a session or an IP spent of each allowance, and when it resets.

    Args:
        session: Anonymous session hash, as stored on its comparisons
        ip: Caller IP. An IPv6 address counts for its whole /64
    """
    for allowance in limits.read_counters(_identities(session, ip)).allowances:
        logger.info(
            f"{allowance.identity} {allowance.pool}: {allowance.used:,} of "
            f"{allowance.limit:,}, {_resets(allowance)}"
            f"{', spent' if allowance.spent else ''}"
        )


def limits_reset(*, session: str | None = None, ip: str | None = None) -> None:
    """
    Give a session or an IP its whole allowances back.

    Args:
        session: Anonymous session hash, as stored on its comparisons
        ip: Caller IP. An IPv6 address counts for its whole /64
    """
    deleted = limits.reset_counters(_identities(session, ip))
    logger.info(f"Reset {deleted} counters")
