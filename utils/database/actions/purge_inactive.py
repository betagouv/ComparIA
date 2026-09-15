import logging
from datetime import datetime

from backend.auth.inactivity import WARNING_DAYS, erasure_date, purge_inactive_users
from backend.config import settings

logger = logging.getLogger("comparia.db")


async def purge_inactive(months: int = 12, apply: bool = False) -> None:
    """Warn then erase accounts not signed in for N months.

    Dry run by default: lists who would get the warning, who would be erased
    and which admins would have matched. Admins are never erased. With --apply,
    sends the warnings and erases the accounts whose notice period is over.
    """
    if not settings.COMPARIA_DB_URI:
        logger.warning("[purge] COMPARIA_DB_URI is not set, nothing to do")
        return

    now = datetime.now()
    report = await purge_inactive_users(months, apply=apply, now=now)
    mode = "applied" if apply else "dry run"
    verb_warn = "warned" if apply else "would warn"
    verb_erase = "erased" if apply else "would erase"

    for user in report.to_warn:
        until = erasure_date(user, months, now)
        logger.info(
            f"[purge] {verb_warn} {user.email} "
            f"(last seen {user.last_seen_at:%Y-%m-%d}, erasure on {until:%Y-%m-%d})"
        )
    for user in report.to_erase:
        logger.info(
            f"[purge] {verb_erase} {user.email} "
            f"(last seen {user.last_seen_at:%Y-%m-%d}, "
            f"warned {user.inactivity_warned_at:%Y-%m-%d})"
        )
    for user in report.warn_failed:
        logger.error(f"[purge] no warning sent to {user.email}, left as is")
    for user in report.admins:
        logger.info(
            f"[purge] admin {user.email} kept "
            f"(last seen {user.last_seen_at:%Y-%m-%d})"
        )
    logger.info(
        f"[purge] {mode}: {len(report.to_warn)} to warn, "
        f"{len(report.to_erase)} to erase, {len(report.admins)} admins kept "
        f"({months} months, {WARNING_DAYS} days notice)"
    )
