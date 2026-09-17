"""
Unit tests for the inactive account purge (no DB, no SMTP).

Run with pytest, or directly:
    uv run python tests/auth/test_purge_inactive.py
"""

import asyncio
import contextlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402

import backend.auth.inactivity as inactivity  # noqa: E402
import utils.database.models  # noqa: E402,F401
from backend.auth.email import _build_inactivity_message  # noqa: E402
from backend.auth.inactivity import (  # noqa: E402
    WARNING_DAYS,
    WindowTooShortError,
    add_months,
    classify,
    erasure_date,
    find_inactive_users,
    purge_inactive_users,
)
from utils.database.models.auth import User  # noqa: E402

NOW = datetime(2026, 9, 15, 12, 0)
MONTHS = 12
DEADLINE = datetime(2025, 9, 15, 12, 0)
NOTICE = timedelta(days=WARNING_DAYS)


@contextlib.contextmanager
def patched(module, **attributes):
    originals = {name: getattr(module, name) for name in attributes}
    for name, value in attributes.items():
        setattr(module, name, value)
    try:
        yield
    finally:
        for name, value in originals.items():
            setattr(module, name, value)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, users):
        self.users = {user.id: user for user in users}
        self.commits = 0

    async def get(self, _model, user_id):
        return self.users.get(user_id)

    async def exec(self, _statement):
        return FakeResult(list(self.users.values()))

    def add(self, _value):
        pass

    async def commit(self):
        self.commits += 1


@contextlib.contextmanager
def purge_context(users, sent=True):
    """Run the purge against in-memory users, catching mails and erasures."""
    session = FakeSession(users)
    mailed = []
    erased = []

    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    async def send_inactivity_warning(to_email, **kwargs):
        mailed.append((to_email, kwargs["erasure_at"]))
        return sent

    async def erase_user_account(user_id):
        erased.append(user_id)

    async def get_app_settings():
        return SimpleNamespace(
            platform_name="Arène de test",
            default_locale="fr",
            primary_color_light="#000091",
            secondary_color_light="#6A6AF4",
        )

    with patched(
        inactivity,
        get_session=get_session,
        send_inactivity_warning=send_inactivity_warning,
        erase_user_account=erase_user_account,
        get_app_settings=get_app_settings,
    ):
        yield session, mailed, erased


def user_seen(last_seen_at, role="user", warned_at=None, deleted_at=None):
    return User(
        email=f"{role}-{last_seen_at:%Y%m%d}@example.test",
        role=role,
        last_seen_at=last_seen_at,
        inactivity_warned_at=warned_at,
        deleted_at=deleted_at,
    )


def test_add_months_clamps_to_the_shorter_month():
    assert add_months(datetime(2026, 3, 31), -1) == datetime(2026, 2, 28)
    assert add_months(datetime(2025, 1, 31), 13) == datetime(2026, 2, 28)
    assert add_months(datetime(2026, 9, 15), -12) == datetime(2025, 9, 15)


def test_selection_window_boundaries():
    minute = timedelta(minutes=1)

    assert classify(user_seen(DEADLINE + NOTICE + minute), MONTHS, NOW) is None
    assert classify(user_seen(DEADLINE + NOTICE), MONTHS, NOW) == "warn"
    assert classify(user_seen(DEADLINE + minute), MONTHS, NOW) == "warn"
    assert classify(user_seen(DEADLINE), MONTHS, NOW) == "warn"
    assert classify(user_seen(DEADLINE - timedelta(days=400)), MONTHS, NOW) == "warn"


def test_a_warned_account_is_erased_only_after_the_notice_period():
    just_warned = user_seen(
        DEADLINE - timedelta(days=1), warned_at=NOW - NOTICE + timedelta(minutes=1)
    )
    notice_over = user_seen(DEADLINE - timedelta(days=1), warned_at=NOW - NOTICE)
    warned_before_deadline = user_seen(
        DEADLINE + timedelta(days=1), warned_at=NOW - NOTICE
    )

    assert classify(just_warned, MONTHS, NOW) is None
    assert classify(notice_over, MONTHS, NOW) == "erase"
    assert classify(warned_before_deadline, MONTHS, NOW) is None


def test_erasure_date_never_cuts_the_notice_short():
    late_find = user_seen(DEADLINE - timedelta(days=200))
    early_warning = user_seen(
        DEADLINE + timedelta(days=20), warned_at=NOW - timedelta(days=20)
    )

    assert erasure_date(late_find, MONTHS, NOW) == NOW + NOTICE
    assert erasure_date(early_warning, MONTHS, NOW) == datetime(2026, 10, 5, 12, 0)


def test_admins_and_deleted_accounts_are_never_erased():
    admin = user_seen(
        DEADLINE - timedelta(days=400), role="admin", warned_at=NOW - NOTICE * 2
    )
    deleted = user_seen(DEADLINE - timedelta(days=400), deleted_at=NOW)

    assert classify(admin, MONTHS, NOW) == "admin"
    assert classify(deleted, MONTHS, NOW) is None


def test_a_window_that_reaches_live_sessions_is_refused():
    """last_seen_at only moves at sign-in: with 90-day sessions, an account
    used every day can look 89 days idle, and a 3-month purge would warn it."""
    active = user_seen(NOW - timedelta(days=1))

    with purge_context([active]) as (_session, mailed, _erased):
        with patched(inactivity.settings, AUTH_SESSION_LENGTH_DAYS=90):
            with pytest.raises(WindowTooShortError):
                asyncio.run(purge_inactive_users(3, apply=True, now=NOW))
            report = asyncio.run(purge_inactive_users(5, apply=True, now=NOW))

    assert mailed == []
    assert report.to_warn == []


def test_find_inactive_users_sorts_accounts_into_the_report():
    to_warn = user_seen(DEADLINE + timedelta(days=10))
    to_erase = user_seen(DEADLINE - timedelta(days=10), warned_at=NOW - NOTICE)
    admin = user_seen(DEADLINE - timedelta(days=10), role="admin")
    active = user_seen(NOW - timedelta(days=1))

    with purge_context([to_warn, to_erase, admin, active]):
        report = asyncio.run(find_inactive_users(MONTHS, NOW))

    assert report.to_warn == [to_warn]
    assert report.to_erase == [to_erase]
    assert report.admins == [admin]


def test_dry_run_touches_nothing():
    to_warn = user_seen(DEADLINE + timedelta(days=10))
    to_erase = user_seen(DEADLINE - timedelta(days=10), warned_at=NOW - NOTICE)

    with purge_context([to_warn, to_erase]) as (session, mailed, erased):
        report = asyncio.run(purge_inactive_users(MONTHS, apply=False, now=NOW))

    assert report.to_warn == [to_warn]
    assert report.to_erase == [to_erase]
    assert mailed == []
    assert erased == []
    assert session.commits == 0
    assert to_warn.inactivity_warned_at is None


def test_apply_warns_once_and_erases_through_erase_user_account():
    to_warn = user_seen(DEADLINE + timedelta(days=10))
    to_erase = user_seen(DEADLINE - timedelta(days=10), warned_at=NOW - NOTICE)
    admin = user_seen(DEADLINE - timedelta(days=10), role="admin")

    with purge_context([to_warn, to_erase, admin]) as (session, mailed, erased):
        first = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))
        second = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert mailed == [(to_warn.email, NOW + NOTICE)]
    assert to_warn.inactivity_warned_at == NOW
    assert session.commits == 1
    assert erased == [to_erase.id, to_erase.id]
    assert first.to_warn == [to_warn]
    assert second.to_warn == []
    assert first.admins == second.admins == [admin]


def test_a_warning_that_could_not_be_sent_is_not_recorded():
    to_warn = user_seen(DEADLINE + timedelta(days=10))

    with purge_context([to_warn], sent=False) as (session, mailed, erased):
        report = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert len(mailed) == 1
    assert to_warn.inactivity_warned_at is None
    assert session.commits == 0
    assert report.to_warn == []
    assert report.warn_failed == [to_warn]


def _parts(message):
    return {
        part.get_content_type(): part.get_content()
        for part in message.walk()
        if not part.is_multipart()
    }


def test_warning_message_is_written_in_the_instance_language():
    message = _build_inactivity_message(
        datetime(2025, 9, 1), datetime(2026, 10, 1), platform_name="Arène & Co"
    )
    parts = _parts(message)

    assert (
        message["Subject"]
        == "Votre compte Arène & Co sera supprimé le 1er octobre 2026"
    )
    assert "depuis le 1er septembre 2025" in parts["text/plain"]
    assert "Arène &amp; Co" in parts["text/html"]
    assert 'lang="fr"' in parts["text/html"]
    assert "deleted on" not in parts["text/plain"]

    danish = _parts(
        _build_inactivity_message(
            datetime(2025, 9, 1), datetime(2026, 10, 1), lang="da"
        )
    )
    assert "siden den 1. september 2025" in danish["text/plain"]
    assert "slettet den 1. oktober 2026" in danish["text/plain"]


def test_warning_message_falls_back_to_english():
    message = _build_inactivity_message(
        datetime(2025, 9, 1), datetime(2026, 10, 1), lang="lt"
    )
    parts = _parts(message)

    assert (
        message["Subject"] == "Your Compar:IA account will be deleted on 1 October 2026"
    )
    assert "since 1 September 2025" in parts["text/plain"]
    assert 'lang="en"' in parts["text/html"]


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
