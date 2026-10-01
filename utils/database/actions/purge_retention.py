import logging

from backend.config import settings
from utils.database.retention import RetentionPeriods, purge_expired_data

logger = logging.getLogger("comparia.db")

DEFAULTS = RetentionPeriods()


async def purge_retention(
    ip_months: int = DEFAULTS.ip_months,
    comparison_months: int = DEFAULTS.comparison_months,
    session_months: int = DEFAULTS.session_months,
    prompt_check_months: int = DEFAULTS.prompt_check_months,
    consent_years: int = DEFAULTS.consent_years,
    apply: bool = False,
) -> None:
    """Blank or delete what the privacy policy says is kept no longer.

    Dry run by default: prints how many rows each rule matches. With --apply,
    blanks the IP of comparisons older than ip-months, cuts comparisons older
    than comparison-months off their account, Matomo visitor and anonymous
    session, and deletes session rows, login codes and 2FA challenges
    session-months after they stopped working, moderation results older than
    prompt-check-months, and consent proofs consent-years after the account
    was deleted or the anonymous session ended. Accounts themselves are
    handled by purge-inactive.
    """
    if not settings.COMPARIA_DB_URI:
        logger.warning("[retention] COMPARIA_DB_URI is not set, nothing to do")
        return

    periods = RetentionPeriods(
        ip_months=ip_months,
        comparison_months=comparison_months,
        session_months=session_months,
        prompt_check_months=prompt_check_months,
        consent_years=consent_years,
    )
    if min(vars(periods).values()) < 1:
        logger.error("[retention] refused: every period must be at least 1")
        raise SystemExit(1)

    report = await purge_expired_data(periods, apply=apply)
    verb = "changed" if apply else "would change"
    for name, count in report.counts.items():
        logger.info(f"[retention] {name}: {verb} {count} rows")
    logger.info(
        f"[retention] {'applied' if apply else 'dry run'}: "
        f"{sum(report.counts.values())} rows ({periods})"
    )
