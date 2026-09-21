import calendar
import logging
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlmodel import select

from backend.auth.email import send_inactivity_warning
from backend.auth.services import erase_user_account
from backend.config import settings
from utils.database.models.auth import ConsentLog, User
from utils.database.session import get_session
from utils.database.settings import get_app_settings

logger = logging.getLogger("languia")

# Days between the warning email and the earliest erasure.
WARNING_DAYS = 30


class WindowTooShortError(ValueError):
    """The purge window would reach accounts whose session may still be in use."""


@dataclass
class InactivityReport:
    to_warn: list[User] = field(default_factory=list)
    to_erase: list[User] = field(default_factory=list)
    admins: list[User] = field(default_factory=list)
    # Only filled by an applied run: warnings that could not be sent, and
    # accounts that changed between selection and erasure, left alone.
    warn_failed: list[User] = field(default_factory=list)
    skipped: list[User] = field(default_factory=list)


def add_months(moment: datetime, months: int) -> datetime:
    """Same day of the month N months away, clamped to the shorter month."""
    index = moment.year * 12 + moment.month - 1 + months
    year, month = divmod(index, 12)
    day = min(moment.day, calendar.monthrange(year, month + 1)[1])
    return moment.replace(year=year, month=month + 1, day=day)


def erasure_date(user: User, months: int, now: datetime) -> datetime:
    """When the account becomes eligible for erasure.

    Never before N months after the last sign-in, and never less than
    WARNING_DAYS after the warning went out (or after now, when it has not
    yet), so a warning always leaves a full notice period.
    """
    deadline = add_months(user.last_seen_at, months)
    notice_end = (user.inactivity_warned_at or now) + timedelta(days=WARNING_DAYS)
    return max(deadline, notice_end)


def check_window(months: int, now: datetime) -> None:
    """last_seen_at moves at sign-in only, so an account used every day on a
    live session can sit AUTH_SESSION_LENGTH_DAYS behind. The warning window
    opens WARNING_DAYS before the deadline and must not reach that far."""
    horizon = add_months(now, -months) + timedelta(days=WARNING_DAYS)
    oldest_live = now - timedelta(days=settings.AUTH_SESSION_LENGTH_DAYS)
    if horizon >= oldest_live:
        raise WindowTooShortError(
            f"{months} months minus {WARNING_DAYS} days of notice reaches accounts "
            f"with a live session (AUTH_SESSION_LENGTH_DAYS="
            f"{settings.AUTH_SESSION_LENGTH_DAYS}); ask for more months"
        )


def classify(user: User, months: int, now: datetime) -> str | None:
    """ "warn", "erase", "admin" or None when the account is not dormant."""
    if user.deleted_at is not None:
        return None
    deadline = add_months(now, -months)
    if user.last_seen_at > deadline + timedelta(days=WARNING_DAYS):
        return None
    if user.role == "admin":
        return "admin"
    if user.inactivity_warned_at is None:
        return "warn"
    if erasure_date(user, months, now) <= now:
        return "erase"
    return None


async def find_inactive_users(
    months: int, now: datetime | None = None
) -> InactivityReport:
    now = now or datetime.now()
    check_window(months, now)
    horizon = add_months(now, -months) + timedelta(days=WARNING_DAYS)
    report = InactivityReport()
    async with get_session() as session:
        result = await session.exec(
            select(User)
            .where(User.deleted_at.is_(None), User.last_seen_at <= horizon)
            .order_by(User.last_seen_at)
        )
        for user in result.all():
            match classify(user, months, now):
                case "warn":
                    report.to_warn.append(user)
                case "erase":
                    report.to_erase.append(user)
                case "admin":
                    report.admins.append(user)
    return report


async def _consent_language(session, user: User) -> str | None:
    """The language the person last accepted the terms in, if recorded."""
    result = await session.exec(
        select(ConsentLog.language)
        .where(ConsentLog.user_id == user.id, ConsentLog.language.is_not(None))
        .order_by(ConsentLog.consented_at.desc())
        .limit(1)
    )
    return result.first()


async def warn_inactive_user(user: User, months: int, now: datetime) -> bool:
    app_settings = await get_app_settings()
    async with get_session() as session:
        locale = await _consent_language(session, user) or app_settings.default_locale
    try:
        sent = await send_inactivity_warning(
            user.email,
            last_seen_at=user.last_seen_at,
            erasure_at=erasure_date(user, months, now),
            platform_name=app_settings.platform_name,
            primary_color=app_settings.primary_color_light,
            secondary_color=app_settings.secondary_color_light,
            locale=locale,
        )
    except (smtplib.SMTPException, OSError) as error:
        # The address stays out of the logs; the id is enough to follow up.
        logger.error(f"[purge] no warning sent to {user.id}: {type(error).__name__}")
        return False
    if not sent:
        return False
    async with get_session() as session:
        row = await session.get(User, user.id)
        if row is None:
            return False
        row.inactivity_warned_at = now
        session.add(row)
        await session.commit()
    return True


async def _erase_unchanged(users: list[User], skipped: list[User]) -> list[User]:
    """Erase the accounts that still look as they did when selected.

    Sending the warnings takes a while, and a sign-in meanwhile moves
    last_seen_at and clears the warning: that account is saved, not erased.
    """
    erased = []
    async with get_session() as session:
        for user in users:
            row = await session.get(User, user.id)
            if (
                row is None
                or row.deleted_at is not None
                or row.inactivity_warned_at is None
                or row.last_seen_at != user.last_seen_at
            ):
                skipped.append(user)
                continue
            await erase_user_account(user.id)
            erased.append(user)
    return erased


async def purge_inactive_users(
    months: int, apply: bool = False, now: datetime | None = None
) -> InactivityReport:
    now = now or datetime.now()
    report = await find_inactive_users(months, now)
    if not apply:
        return report
    warned = []
    for user in report.to_warn:
        if await warn_inactive_user(user, months, now):
            warned.append(user)
        else:
            report.warn_failed.append(user)
    report.to_warn = warned
    report.to_erase = await _erase_unchanged(report.to_erase, report.skipped)
    return report
