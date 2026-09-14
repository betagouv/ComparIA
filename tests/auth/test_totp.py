"""
Unit tests for the admins' authenticator second factor (no DB, no Redis).

Run with pytest, or directly:
    uv run python tests/auth/test_totp.py
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ.setdefault("COMPARIA_DB_URI", "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pyotp  # noqa: E402
import pytest  # noqa: E402
from cryptography.fernet import Fernet  # noqa: E402

import backend.auth.services as auth_services  # noqa: E402
import backend.auth.totp as auth_totp  # noqa: E402
import utils.database.models  # noqa: E402,F401 needed before importing the router
from utils.database.models.auth import TotpChallenge, User, UserTotp  # noqa: E402


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

    def first(self):
        return self.rows[0] if self.rows else None

    def all(self):
        return self.rows


class FakeSession:
    """Answers `exec` from a queue of result rows, in call order, and keeps
    the statements a service runs so a test can replay them."""

    def __init__(self, user=None, *results):
        self.user = user
        self.results = list(results)
        self.statements = []
        self.added = []
        self.commits = 0

    async def get(self, _model, _id):
        return self.user

    async def exec(self, _statement):
        return FakeResult(self.results.pop(0) if self.results else [])

    async def execute(self, statement):
        self.statements.append(statement)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        pass

    async def commit(self):
        self.commits += 1


@contextlib.contextmanager
def fake_session(session, *modules):
    @contextlib.asynccontextmanager
    async def get_session():
        yield session

    with contextlib.ExitStack() as stack:
        for module in modules or (auth_totp,):
            stack.enter_context(patched(module, get_session=get_session))
        yield session


def updates_on(statements, table_name):
    return [
        s.compile().params
        for s in statements
        if s.is_update and s.table.name == table_name
    ]


SECRET = pyotp.random_base32()


def code_at(step, secret=SECRET):
    return pyotp.TOTP(secret).generate_otp(step)


def enrolled(user, secret=SECRET, last_used_step=None):
    return UserTotp(
        user_id=user.id,
        secret_encrypted=auth_totp.encrypt_secret(secret),
        confirmed_at=datetime.now(),
        last_used_step=last_used_step,
    )


def challenge_for(user, attempts=0):
    return TotpChallenge(
        user_id=user.id,
        token_hash=auth_services._hash("challenge-token"),
        expires_at=datetime.now() + timedelta(minutes=10),
        attempts=attempts,
    )


# Codes


def test_a_code_matches_its_own_step_and_one_step_either_side():
    step = auth_totp.current_step()
    for delta in (-1, 0, 1):
        assert auth_totp.matching_step(SECRET, code_at(step + delta)) == step + delta
    for delta in (-2, 2):
        assert auth_totp.matching_step(SECRET, code_at(step + delta)) is None


def test_a_code_is_refused_once_its_step_has_been_used():
    step = auth_totp.current_step()
    assert auth_totp.matching_step(SECRET, code_at(step), last_used_step=step) is None
    assert (
        auth_totp.matching_step(SECRET, code_at(step), last_used_step=step - 1) == step
    )


def test_a_code_must_be_six_digits():
    step = auth_totp.current_step()
    assert auth_totp.matching_step(SECRET, code_at(step)[:5]) is None
    assert auth_totp.matching_step(SECRET, " " + code_at(step)) is None
    assert auth_totp.matching_step(SECRET, "abcdef") is None


def test_every_candidate_is_compared_before_answering():
    """Constant time: the loop must not stop at the first match."""
    calls = []
    real = auth_totp.hmac.compare_digest

    def counting(a, b):
        calls.append(1)
        return real(a, b)

    with patched(auth_totp.hmac, compare_digest=counting):
        auth_totp.matching_step(SECRET, code_at(auth_totp.current_step() - 1))
    assert len(calls) == 3


def test_the_issuer_never_carries_a_colon():
    assert auth_totp.issuer_from("compar:IA") == "compar IA"
    assert auth_totp.issuer_from("  Arène   de test ") == "Arène de test"
    assert auth_totp.issuer_from("") == "ComparIA"
    assert auth_totp.issuer_from(None) == "ComparIA"


def test_the_provisioning_uri_names_issuer_and_account():
    uri = auth_totp.provisioning_uri(SECRET, "admin@example.test", "compar IA")
    assert uri.startswith("otpauth://totp/compar%20IA:admin%40example.test?")
    assert f"secret={SECRET}" in uri
    assert "issuer=compar%20IA" in uri
    assert auth_totp.qr_data_uri(uri).startswith("data:image/svg+xml")


# Secrets at rest


def test_secrets_round_trip_through_the_key():
    token = auth_totp.encrypt_secret(SECRET)
    assert token != SECRET
    assert auth_totp.decrypt_secret(token) == SECRET


def test_an_older_key_still_decrypts_and_is_flagged_for_reencryption():
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    with patched(auth_totp.settings, AUTH_TOTP_ENCRYPTION_KEY=old_key):
        auth_totp._fernet.cache_clear()
        old_token = auth_totp.encrypt_secret(SECRET)
    with patched(auth_totp.settings, AUTH_TOTP_ENCRYPTION_KEY=f"{new_key},{old_key}"):
        auth_totp._fernet.cache_clear()
        assert auth_totp.decrypt_secret(old_token) == SECRET
        assert auth_totp._needs_reencryption(old_token)
        assert not auth_totp._needs_reencryption(auth_totp.encrypt_secret(SECRET))
    auth_totp._fernet.cache_clear()


def test_a_secret_from_an_unknown_key_reads_as_missing_not_as_unenrolled():
    with patched(
        auth_totp.settings, AUTH_TOTP_ENCRYPTION_KEY=Fernet.generate_key().decode()
    ):
        auth_totp._fernet.cache_clear()
        token = auth_totp.encrypt_secret(SECRET)
    auth_totp._fernet.cache_clear()
    assert auth_totp.decrypt_secret(token) is None


# First factor


def test_sign_in_opens_a_session_when_no_authenticator_is_enrolled():
    user = User(email="admin@example.test")
    login_code = utils.database.models.LoginCode(
        user_id=user.id,
        code_hash=auth_services._hash("123456"),
        expires_at=datetime.now() + timedelta(minutes=5),
    )
    session = FakeSession(user, [user], [login_code], [])

    with fake_session(session, auth_services):
        result = asyncio.run(
            auth_services.verify_login_code(
                "admin@example.test", "123456", "192.0.2.1", None, None
            )
        )

    assert result.kind == "session"
    assert login_code.used_at is not None
    assert [type(a).__name__ for a in session.added] == ["AuthSession"]


def test_sign_in_hands_back_a_challenge_when_an_authenticator_is_enrolled():
    user = User(email="admin@example.test")
    login_code = utils.database.models.LoginCode(
        user_id=user.id,
        code_hash=auth_services._hash("123456"),
        expires_at=datetime.now() + timedelta(minutes=5),
    )
    session = FakeSession(user, [user], [login_code], [uuid.uuid4()])

    with fake_session(session, auth_services):
        result = asyncio.run(
            auth_services.verify_login_code(
                "admin@example.test", "123456", "192.0.2.1", None, None
            )
        )

    assert result.kind == "totp_challenge"
    assert login_code.used_at is not None
    assert session.commits == 1
    added = session.added
    assert [type(a).__name__ for a in added] == ["TotpChallenge"]
    assert added[0].token_hash == auth_services._hash(result.token)
    assert added[0].user_id == user.id


def test_an_invite_accepted_by_an_enrolled_admin_is_challenged_too():
    user = User(email="admin@example.test")
    invite = utils.database.models.auth.InviteToken(
        user_id=user.id,
        invited_by=uuid.uuid4(),
        token_hash=auth_services._hash("invite"),
        expires_at=datetime.now() + timedelta(hours=1),
    )
    session = FakeSession(user, [invite], [uuid.uuid4()])

    with fake_session(session, auth_services):
        result = asyncio.run(
            auth_services.accept_invite("invite", "192.0.2.1", None, None)
        )

    assert result.kind == "totp_challenge"
    assert invite.used_at is not None


# Second factor


def run_challenge(session, code):
    with fake_session(session, auth_totp, auth_services):
        return asyncio.run(
            auth_totp.verify_totp_challenge(
                "challenge-token", code, "192.0.2.1", "UA", None
            )
        )


def test_a_valid_code_consumes_the_challenge_and_opens_the_session():
    user = User(email="admin@example.test")
    totp = enrolled(user)
    challenge = challenge_for(user)
    session = FakeSession(user, [challenge], [totp], [])
    step = auth_totp.current_step()

    token = run_challenge(session, code_at(step))

    assert challenge.used_at is not None
    assert totp.last_used_step == step
    assert session.commits == 1
    sessions = [a for a in session.added if type(a).__name__ == "AuthSession"]
    assert len(sessions) == 1
    assert sessions[0].token_hash == auth_services._hash(token)
    assert sessions[0].ip == "192.0.2.1"


def test_a_wrong_code_costs_an_attempt_and_is_committed():
    user = User(email="admin@example.test")
    challenge = challenge_for(user)
    session = FakeSession(user, [challenge], [enrolled(user)])

    with pytest.raises(auth_totp.InvalidTotpCodeError):
        run_challenge(session, "000000")

    assert challenge.attempts == 1
    assert challenge.used_at is None
    assert session.commits == 1


def test_the_last_allowed_wrong_code_kills_the_challenge():
    user = User(email="admin@example.test")
    challenge = challenge_for(user, attempts=auth_totp._TOTP_CHALLENGE_MAX_ATTEMPTS - 1)
    session = FakeSession(user, [challenge], [enrolled(user)])

    with pytest.raises(auth_totp.TotpChallengeExpiredError):
        run_challenge(session, "000000")

    assert challenge.attempts == auth_totp._TOTP_CHALLENGE_MAX_ATTEMPTS


def test_an_exhausted_challenge_refuses_even_the_right_code():
    user = User(email="admin@example.test")
    challenge = challenge_for(user, attempts=auth_totp._TOTP_CHALLENGE_MAX_ATTEMPTS)
    session = FakeSession(user, [challenge], [enrolled(user)])

    with pytest.raises(auth_totp.TotpChallengeExpiredError):
        run_challenge(session, code_at(auth_totp.current_step()))
    assert session.commits == 0


def test_a_missing_challenge_is_expired():
    session = FakeSession(None, [])
    with pytest.raises(auth_totp.TotpChallengeExpiredError):
        run_challenge(session, "123456")


def test_a_challenge_dies_with_the_authenticator_it_was_issued_for():
    """A peer reset between the email code and the authenticator code."""
    user = User(email="admin@example.test")
    session = FakeSession(user, [challenge_for(user)], [])
    with pytest.raises(auth_totp.TotpChallengeExpiredError):
        run_challenge(session, code_at(auth_totp.current_step()))


def test_a_code_already_used_at_sign_in_is_refused_again():
    user = User(email="admin@example.test")
    step = auth_totp.current_step()
    challenge = challenge_for(user)
    session = FakeSession(user, [challenge], [enrolled(user, last_used_step=step)])

    with pytest.raises(auth_totp.InvalidTotpCodeError):
        run_challenge(session, code_at(step))


def test_a_secret_under_an_older_key_is_rewritten_at_sign_in():
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    user = User(email="admin@example.test")
    with patched(auth_totp.settings, AUTH_TOTP_ENCRYPTION_KEY=old_key):
        auth_totp._fernet.cache_clear()
        totp = enrolled(user)
    old_token = totp.secret_encrypted

    with patched(auth_totp.settings, AUTH_TOTP_ENCRYPTION_KEY=f"{new_key},{old_key}"):
        auth_totp._fernet.cache_clear()
        session = FakeSession(user, [challenge_for(user)], [totp], [])
        run_challenge(session, code_at(auth_totp.current_step()))
        assert totp.secret_encrypted != old_token
        assert not auth_totp._needs_reencryption(totp.secret_encrypted)
    auth_totp._fernet.cache_clear()


# Enrolment


def test_first_enrolment_needs_no_code_and_leaves_nothing_live():
    user = User(email="admin@example.test")
    session = FakeSession(user, [])

    with fake_session(session):
        setup = asyncio.run(auth_totp.start_totp_setup(user, None, "compar:IA"))

    assert session.commits == 1
    [totp] = session.added
    assert totp.user_id == user.id
    assert totp.secret_encrypted is None
    assert totp.confirmed_at is None
    assert auth_totp.decrypt_secret(totp.pending_secret_encrypted) == setup.secret
    assert "compar%20IA" in setup.otpauth_uri
    assert setup.qr_svg.startswith("data:image/svg+xml")


def test_changing_device_needs_a_code_from_the_current_one():
    user = User(email="admin@example.test")
    totp = enrolled(user)

    with fake_session(FakeSession(user, [totp])):
        with pytest.raises(auth_totp.TotpCodeRequiredError):
            asyncio.run(auth_totp.start_totp_setup(user, None, None))

    with fake_session(FakeSession(user, [totp])):
        with pytest.raises(auth_totp.InvalidTotpCodeError):
            asyncio.run(auth_totp.start_totp_setup(user, "000000", None))
    assert totp.pending_secret_encrypted is None

    live = totp.secret_encrypted
    session = FakeSession(user, [totp])
    with fake_session(session):
        setup = asyncio.run(
            auth_totp.start_totp_setup(user, code_at(auth_totp.current_step()), None)
        )
    assert totp.secret_encrypted == live
    assert auth_totp.decrypt_secret(totp.pending_secret_encrypted) == setup.secret
    assert totp.last_used_step == auth_totp.current_step()


def test_confirming_promotes_the_pending_secret_and_signs_other_sessions_out():
    user = User(email="admin@example.test")
    new_secret = pyotp.random_base32()
    totp = enrolled(user)
    totp.pending_secret_encrypted = auth_totp.encrypt_secret(new_secret)
    totp.pending_created_at = datetime.now()
    session = FakeSession(user, [totp])
    step = auth_totp.current_step()

    with fake_session(session, auth_totp, auth_services):
        asyncio.run(
            auth_totp.confirm_totp_setup(user, code_at(step, new_secret), "keep-me")
        )

    assert auth_totp.decrypt_secret(totp.secret_encrypted) == new_secret
    assert totp.pending_secret_encrypted is None
    assert totp.pending_created_at is None
    assert totp.confirmed_at is not None
    assert totp.last_used_step == step
    [revocation] = updates_on(session.statements, "auth_session")
    assert revocation["token_hash_1"] == auth_services._hash("keep-me")
    assert revocation["revoked_at"] is not None


def test_confirming_needs_a_fresh_pending_secret():
    user = User(email="admin@example.test")

    with fake_session(FakeSession(user, [])):
        with pytest.raises(auth_totp.TotpSetupMissingError):
            asyncio.run(auth_totp.confirm_totp_setup(user, "123456", "t"))

    totp = UserTotp(
        user_id=user.id,
        pending_secret_encrypted=auth_totp.encrypt_secret(SECRET),
        pending_created_at=datetime.now() - timedelta(minutes=20),
    )
    with fake_session(FakeSession(user, [totp])):
        with pytest.raises(auth_totp.TotpSetupMissingError):
            asyncio.run(
                auth_totp.confirm_totp_setup(
                    user, code_at(auth_totp.current_step()), "t"
                )
            )
    assert totp.confirmed_at is None


def test_confirming_with_a_wrong_code_changes_nothing():
    user = User(email="admin@example.test")
    totp = UserTotp(
        user_id=user.id,
        pending_secret_encrypted=auth_totp.encrypt_secret(SECRET),
        pending_created_at=datetime.now(),
    )
    session = FakeSession(user, [totp])
    with fake_session(session, auth_totp, auth_services):
        with pytest.raises(auth_totp.InvalidTotpCodeError):
            asyncio.run(auth_totp.confirm_totp_setup(user, "000000", "t"))
    assert totp.confirmed_at is None
    assert totp.pending_secret_encrypted is not None
    assert session.commits == 0
    assert updates_on(session.statements, "auth_session") == []


if __name__ == "__main__":
    import pytest as _pytest

    sys.exit(_pytest.main([__file__, "-q"]))
