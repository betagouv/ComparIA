import calendar
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlmodel import select

from backend.auth.email import send_inactivity_warning
from backend.auth.services import erase_user_account
from backend.config import settings
from utils.database.models.auth import User
from utils.database.session import get_session
from utils.database.settings import get_app_settings

# Days between the warning email and the earliest erasure.
WARNING_DAYS = 30


class WindowTooShortError(ValueError):
    """The purge window would reach accounts whose session may still be in use."""


@dataclass
class InactivityReport:
    to_warn: list[User] = field(default_factory=list)
    to_erase: list[User] = field(default_factory=list)
    admins: list[User] = field(default_factory=list)
    # Only filled by an applied run: warnings that could not be sent.
    warn_failed: list[User] = field(default_factory=list)


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


async def warn_inactive_user(user: User, months: int, now: datetime) -> bool:
    app_settings = await get_app_settings()
    sent = await send_inactivity_warning(
        user.email,
        last_seen_at=user.last_seen_at,
        erasure_at=erasure_date(user, months, now),
        platform_name=app_settings.platform_name,
        primary_color=app_settings.primary_color_light,
        secondary_color=app_settings.secondary_color_light,
        locale=app_settings.default_locale,
    )
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
    for user in report.to_erase:
        await erase_user_account(user.id)
    return report
