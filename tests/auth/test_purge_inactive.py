"""
Unit tests for the inactive account purge (no DB, no SMTP).

Run with pytest, or directly:
    uv run python tests/auth/test_purge_inactive.py
"""

import asyncio
import contextlib
import os
import smtplib
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402

import backend.admin.services as admin_services  # noqa: E402
import backend.auth.email as email  # noqa: E402
import backend.auth.inactivity as inactivity  # noqa: E402
import backend.auth.services as auth_services  # noqa: E402
import utils.database.models  # noqa: E402,F401
from backend.admin.services import create_user  # noqa: E402
from backend.auth.email import (  # noqa: E402
    _build_inactivity_message,
    send_inactivity_warning,
)
from backend.auth.inactivity import (  # noqa: E402
    WARNING_DAYS,
    WindowTooShortError,
    add_months,
    classify,
    erasure_date,
    find_inactive_users,
    purge_inactive_users,
)
from backend.auth.services import create_invite  # noqa: E402
from utils.database.models.auth import (  # noqa: E402
    AuthSession,
    ConsentLog,
    InviteToken,
    User,
    UserUpsert,
)

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

    def first(self):
        return self.rows[0] if self.rows else None


class FakeSession:
    """Answers the purge's queries from memory, keyed on the selected model."""

    def __init__(self, users, languages=None, invited=(), never_signed_in=()):
        self.users = {user.id: user for user in users}
        # user id -> language of their latest consent
        self.languages = languages or {}
        # user ids holding an invite that can still be accepted
        self.invited = set(invited)
        # user ids without any session row; everyone else has signed in
        self.never_signed_in = set(never_signed_in)
        # user id -> the row as re-read later, when it differs from the list
        self.refreshed = {}
        self.commits = 0

    async def get(self, _model, user_id):
        return self.refreshed.get(user_id, self.users.get(user_id))

    async def exec(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        if entity is User:
            return FakeResult(list(self.users.values()))
        if entity is AuthSession:
            return FakeResult(
                [
                    user_id
                    for user_id in self.users
                    if user_id not in self.never_signed_in
                ]
            )
        if entity is InviteToken:
            return FakeResult(
                [user_id for user_id in self.users if user_id in self.invited]
            )
        if entity is ConsentLog:
            user_id = statement.whereclause.clauses[0].right.value
            language = self.languages.get(user_id)
            return FakeResult([language] if language else [])
        raise AssertionError(f"unexpected query on {entity.__name__}")

    def add(self, _value):
        pass

    async def commit(self):
        self.commits += 1


@contextlib.contextmanager
def purge_context(
    users, sent=True, failing=(), languages=None, invited=(), never_signed_in=()
):
    """Run the purge against in-memory users, catching mails and erasures.

    `failing` lists the addresses whose delivery raises, as a dead SMTP
    server would.
    """
    session = FakeSession(
        users, languages=languages, invited=invited, never_signed_in=never_signed_in
    )
    mailed = []
    locales = []
    erased = []

    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    async def send_inactivity_warning(to_email, **kwargs):
        mailed.append((to_email, kwargs["erasure_at"]))
        locales.append(kwargs["locale"])
        if to_email in failing:
            raise smtplib.SMTPServerDisconnected("Connection unexpectedly closed")
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
        yield session, mailed, erased, locales


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

    with purge_context([active]) as (_session, mailed, _erased, _locales):
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


def test_a_row_that_never_signed_in_is_erased_without_a_warning():
    """Asking for a login code creates the row; if the code was never used
    there was no account to warn about, and nothing to read the email."""
    past_deadline = user_seen(DEADLINE - timedelta(days=1))
    in_the_window = user_seen(DEADLINE + timedelta(days=1))
    to_warn = user_seen(DEADLINE + timedelta(days=2))
    never = {past_deadline.id, in_the_window.id}

    assert classify(past_deadline, MONTHS, NOW, signed_in=False) == "never_signed_in"
    assert classify(in_the_window, MONTHS, NOW, signed_in=False) is None

    with purge_context(
        [past_deadline, in_the_window, to_warn], never_signed_in=never
    ) as (_session, mailed, erased, _locales):
        dry = asyncio.run(purge_inactive_users(MONTHS, apply=False, now=NOW))
        assert erased == []
        report = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert dry.never_signed_in == [past_deadline]
    assert dry.to_warn == [to_warn]
    assert [email for email, _ in mailed] == [to_warn.email]
    assert erased == [past_deadline.id]
    assert report.never_signed_in == [past_deadline]


def test_an_account_with_a_pending_invite_is_left_alone():
    """A re-invited account keeps its old last_seen_at until the invite is
    accepted, which may take a while; the invite's own expiry rules there."""
    invited = user_seen(DEADLINE - timedelta(days=10))
    to_warn = user_seen(DEADLINE - timedelta(days=5))

    with purge_context([invited, to_warn], invited={invited.id}):
        report = asyncio.run(find_inactive_users(MONTHS, NOW))

    assert classify(invited, MONTHS, NOW, invited=True) is None
    assert report.to_warn == [to_warn]


class RevivalSession:
    """Just enough session for the two paths that revive a deleted row."""

    def __init__(self, user):
        self.user = user
        self.added = []

    async def exec(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([self.user] if entity is User else [])

    def add(self, value):
        self.added.append(value)

    async def delete(self, _value):
        pass

    async def flush(self):
        pass

    async def commit(self):
        pass

    async def refresh(self, _value):
        pass


@pytest.mark.parametrize("path", ["invite", "admin"])
def test_reviving_a_deleted_account_restarts_its_inactivity_clock(path):
    deleted = user_seen(
        DEADLINE - timedelta(days=400), warned_at=NOW - NOTICE, deleted_at=NOW
    )
    deleted.created_at = deleted.last_seen_at
    session = RevivalSession(deleted)

    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    before = datetime.now()
    if path == "invite":
        with patched(auth_services, get_session=get_session):
            asyncio.run(create_invite(deleted.email, invited_by=uuid.uuid4()))
    else:
        with patched(admin_services, get_session=get_session):
            asyncio.run(create_user(UserUpsert(email=deleted.email, role="user")))

    assert deleted.deleted_at is None
    assert deleted.inactivity_warned_at is None
    assert deleted.last_seen_at >= before
    assert classify(deleted, MONTHS, NOW) is None


def test_dry_run_touches_nothing():
    to_warn = user_seen(DEADLINE + timedelta(days=10))
    to_erase = user_seen(DEADLINE - timedelta(days=10), warned_at=NOW - NOTICE)

    with purge_context([to_warn, to_erase]) as (session, mailed, erased, _locales):
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

    with purge_context([to_warn, to_erase, admin]) as (
        session,
        mailed,
        erased,
        _locales,
    ):
        first = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))
        second = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert mailed == [(to_warn.email, NOW + NOTICE)]
    assert to_warn.inactivity_warned_at == NOW
    assert session.commits == 1
    assert erased == [to_erase.id, to_erase.id]
    assert first.to_warn == [to_warn]
    assert second.to_warn == []
    assert first.admins == second.admins == [admin]


def test_warning_is_written_in_the_consent_language_else_the_instance_one():
    danish = user_seen(DEADLINE + timedelta(days=10))
    unknown = user_seen(DEADLINE + timedelta(days=9))

    with purge_context([danish, unknown], languages={danish.id: "da"}) as (
        _session,
        _mailed,
        _erased,
        locales,
    ):
        asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert locales == ["da", "fr"]


def test_an_account_signed_into_during_the_run_is_not_erased():
    to_erase = user_seen(DEADLINE - timedelta(days=10), warned_at=NOW - NOTICE)
    revived = user_seen(DEADLINE - timedelta(days=20), warned_at=NOW - NOTICE)
    signed_in = User(
        id=revived.id, email=revived.email, last_seen_at=NOW, inactivity_warned_at=None
    )

    with purge_context([to_erase, revived]) as (session, _mailed, erased, _locales):
        session.refreshed[revived.id] = signed_in
        report = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert erased == [to_erase.id]
    assert report.to_erase == [to_erase]
    assert report.skipped == [revived]


def test_a_warning_that_could_not_be_sent_is_not_recorded():
    to_warn = user_seen(DEADLINE + timedelta(days=10))

    with purge_context([to_warn], sent=False) as (session, mailed, erased, _locales):
        report = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert len(mailed) == 1
    assert to_warn.inactivity_warned_at is None
    assert session.commits == 0
    assert report.to_warn == []
    assert report.warn_failed == [to_warn]


def test_a_delivery_failure_skips_the_account_and_the_run_goes_on():
    unreachable = user_seen(DEADLINE + timedelta(days=10))
    to_warn = user_seen(DEADLINE + timedelta(days=5))
    to_erase = user_seen(DEADLINE - timedelta(days=10), warned_at=NOW - NOTICE)

    with purge_context(
        [unreachable, to_warn, to_erase], failing={unreachable.email}
    ) as (session, mailed, erased, _locales):
        report = asyncio.run(purge_inactive_users(MONTHS, apply=True, now=NOW))

    assert [email for email, _ in mailed] == [unreachable.email, to_warn.email]
    assert unreachable.inactivity_warned_at is None
    assert to_warn.inactivity_warned_at == NOW
    assert session.commits == 1
    assert erased == [to_erase.id]
    assert report.warn_failed == [unreachable]
    assert report.to_warn == [to_warn]


@pytest.mark.parametrize("debug", [False, True])
def test_without_smtp_the_warning_is_reported_as_not_sent(debug):
    """A debug instance logs login codes instead of mailing them, but a
    warning it never sent must not count as sent: the account would be
    erased on the next run without anyone hearing about it."""
    with patched(email.settings, SMTP_HOST=None, LANGUIA_DEBUG=debug):
        sent = asyncio.run(
            send_inactivity_warning("someone@example.test", NOW - NOTICE, NOW)
        )

    assert sent is False


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
    assert "pour le conserver :" in parts["text/plain"]
    assert "pour le conserver&nbsp;:" in parts["text/html"]
    assert "Arène &amp; Co" in parts["text/html"]
    assert '<html lang="fr">' in parts["text/html"]
    assert "Message automatique envoyé par Arène &amp; Co." in parts["text/html"]
    assert "deleted on" not in parts["text/plain"]

    danish = _parts(
        _build_inactivity_message(
            datetime(2025, 9, 1), datetime(2026, 10, 1), locale="da"
        )
    )
    assert "siden den 1. september 2025" in danish["text/plain"]
    assert "slettet den 1. oktober 2026" in danish["text/plain"]


def test_warning_message_follows_the_locale_and_falls_back_to_french():
    english = _build_inactivity_message(
        datetime(2025, 9, 1), datetime(2026, 10, 1), locale="en-GB"
    )
    unknown = _build_inactivity_message(
        datetime(2025, 9, 1), datetime(2026, 10, 1), locale="lt"
    )
    parts = _parts(english)

    assert (
        english["Subject"] == "Your Compar:IA account will be deleted on 1 October 2026"
    )
    assert "since 1 September 2025" in parts["text/plain"]
    assert "nothing to do" in parts["text/plain"]
    assert '<html lang="en">' in parts["text/html"]
    assert (
        unknown["Subject"] == "Votre compte Compar:IA sera supprimé le 1er octobre 2026"
    )


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
