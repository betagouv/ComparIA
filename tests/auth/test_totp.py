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
import utils.secrets as secrets_store  # noqa: E402
from utils.database.models.auth import TotpChallenge, User, UserTotp  # noqa: E402
from utils.secrets import SecretUnreadableError  # noqa: E402


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
        self.exec_statements = []
        self.added = []
        self.commits = 0

    async def get(self, _model, _id):
        return self.user

    async def exec(self, statement):
        self.exec_statements.append(statement)
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


@contextlib.contextmanager
def under_a_key_we_no_longer_have():
    """Whatever is encrypted inside cannot be read back outside."""
    with patched(
        secrets_store.settings, COMPARIA_ENCRYPTION_KEY=Fernet.generate_key().decode()
    ):
        secrets_store._fernet.cache_clear()
        yield
    secrets_store._fernet.cache_clear()


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


def test_a_code_must_be_six_ascii_digits():
    step = auth_totp.current_step()
    assert auth_totp.matching_step(SECRET, code_at(step)[:5]) is None
    assert auth_totp.matching_step(SECRET, " " + code_at(step)) is None
    assert auth_totp.matching_step(SECRET, "abcdef") is None
    # Other scripts' digits match `\d` and would crash the comparison.
    assert auth_totp.matching_step(SECRET, "١٢٣٤٥٦") is None


def test_the_routes_refuse_non_ascii_digits_with_a_422():
    with routed() as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post("/auth/totp/verify", json={"code": "١٢٣٤٥٦"})
    assert r.status_code == 422


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


def test_a_key_fernet_would_refuse_is_refused_at_boot():
    from backend.config import check_encryption_keys

    valid = Fernet.generate_key().decode()
    check_encryption_keys(valid)
    check_encryption_keys(f" {valid} , {Fernet.generate_key().decode()}")

    hex_key = os.urandom(32).hex()
    for bad in ("", "  ,  ", hex_key, f"{valid},{hex_key}", "not-base64!"):
        with pytest.raises(RuntimeError) as refused:
            check_encryption_keys(bad)
        assert "COMPARIA_ENCRYPTION_KEY" in str(refused.value)
        assert "Fernet.generate_key()" in str(refused.value)


def test_secrets_round_trip_through_the_key():
    token = auth_totp.encrypt_secret(SECRET)
    assert token != SECRET
    assert auth_totp.decrypt_secret(token) == SECRET


def test_an_older_key_still_decrypts_and_is_flagged_for_reencryption():
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    with patched(secrets_store.settings, COMPARIA_ENCRYPTION_KEY=old_key):
        secrets_store._fernet.cache_clear()
        old_token = auth_totp.encrypt_secret(SECRET)
    with patched(
        secrets_store.settings, COMPARIA_ENCRYPTION_KEY=f"{new_key},{old_key}"
    ):
        secrets_store._fernet.cache_clear()
        assert auth_totp.decrypt_secret(old_token) == SECRET
        assert secrets_store.needs_reencryption(old_token)
        assert not secrets_store.needs_reencryption(auth_totp.encrypt_secret(SECRET))
    secrets_store._fernet.cache_clear()


def test_a_secret_from_an_unknown_key_reads_as_unreadable_not_as_unenrolled():
    with under_a_key_we_no_longer_have():
        token = auth_totp.encrypt_secret(SECRET)
    with pytest.raises(SecretUnreadableError):
        auth_totp.decrypt_secret(token)

    # The row still says enrolled: the admin stays gated, nobody gets in on
    # an email code alone because a key went missing.
    user = User(email="admin@example.test", role="admin")
    with fake_session(FakeSession(user, [uuid.uuid4()])):
        assert asyncio.run(auth_totp.has_confirmed_totp(user.id))


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


def test_a_secret_no_key_opens_is_neither_a_wrong_code_nor_a_dead_challenge():
    user = User(email="admin@example.test")
    with under_a_key_we_no_longer_have():
        totp = enrolled(user)
    challenge = challenge_for(user)
    session = FakeSession(user, [challenge], [totp])

    with pytest.raises(SecretUnreadableError):
        run_challenge(session, code_at(auth_totp.current_step()))

    assert challenge.attempts == 0
    assert challenge.used_at is None
    assert session.commits == 0


def test_wrong_codes_are_capped_per_account_across_challenges():
    """Each new email code buys a fresh challenge with fresh attempts, so the
    hour's failures are summed over every challenge of the account."""
    user = User(email="admin@example.test")
    cap = auth_totp._TOTP_MAX_FAILS_PER_USER_PER_HOUR
    challenge = challenge_for(user)
    session = FakeSession(user, [challenge], [enrolled(user)], [cap])

    with pytest.raises(auth_totp.TotpChallengeExpiredError):
        run_challenge(session, code_at(auth_totp.current_step()))

    assert challenge.attempts == 0
    assert challenge.used_at is None
    assert session.commits == 0

    challenge = challenge_for(user)
    session = FakeSession(user, [challenge], [enrolled(user)], [cap - 1])
    run_challenge(session, code_at(auth_totp.current_step()))
    assert challenge.used_at is not None
    assert session.commits == 1


def test_the_account_cap_is_read_over_the_last_hour_of_challenges():
    user = User(email="admin@example.test")
    session = FakeSession(user, [challenge_for(user)], [enrolled(user)], [0])
    before = datetime.now()
    run_challenge(session, code_at(auth_totp.current_step()))

    [summed] = [
        s
        for s in session.exec_statements
        if "sum(auth_totp_challenge.attempts)" in str(s)
    ]
    params = summed.compile().params
    assert params["user_id_1"] == user.id
    window_start = params["created_at_1"]
    assert before - timedelta(hours=1, seconds=5) <= window_start
    assert window_start <= datetime.now() - timedelta(hours=1)


def test_a_secret_under_an_older_key_is_rewritten_at_sign_in():
    old_key = Fernet.generate_key().decode()
    new_key = Fernet.generate_key().decode()
    user = User(email="admin@example.test")
    with patched(secrets_store.settings, COMPARIA_ENCRYPTION_KEY=old_key):
        secrets_store._fernet.cache_clear()
        totp = enrolled(user)
    old_token = totp.secret_encrypted

    with patched(
        secrets_store.settings, COMPARIA_ENCRYPTION_KEY=f"{new_key},{old_key}"
    ):
        secrets_store._fernet.cache_clear()
        session = FakeSession(user, [challenge_for(user)], [totp], [])
        run_challenge(session, code_at(auth_totp.current_step()))
        assert totp.secret_encrypted != old_token
        assert not secrets_store.needs_reencryption(totp.secret_encrypted)
    secrets_store._fernet.cache_clear()


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


def test_changing_device_with_an_unreadable_secret_is_not_a_wrong_code():
    user = User(email="admin@example.test")
    with under_a_key_we_no_longer_have():
        totp = enrolled(user)
    session = FakeSession(user, [totp])

    with fake_session(session):
        with pytest.raises(SecretUnreadableError):
            asyncio.run(
                auth_totp.start_totp_setup(
                    user, code_at(auth_totp.current_step()), None
                )
            )
    assert totp.pending_secret_encrypted is None
    assert session.commits == 0


def test_confirming_an_unreadable_pending_secret_is_not_a_missing_one():
    user = User(email="admin@example.test")
    with under_a_key_we_no_longer_have():
        pending = auth_totp.encrypt_secret(SECRET)
    totp = UserTotp(
        user_id=user.id,
        pending_secret_encrypted=pending,
        pending_created_at=datetime.now(),
    )
    session = FakeSession(user, [totp])

    with fake_session(session, auth_totp, auth_services):
        with pytest.raises(SecretUnreadableError):
            asyncio.run(
                auth_totp.confirm_totp_setup(
                    user, code_at(auth_totp.current_step()), "t"
                )
            )
    assert totp.confirmed_at is None
    assert totp.pending_secret_encrypted == pending
    assert session.commits == 0


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
    # One transaction: the revocation is issued before the single commit.
    assert session.commits == 1


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


# Routes


@contextlib.contextmanager
def routed(**fakes):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import backend.auth.router as auth_router

    app = FastAPI()
    app.include_router(auth_router.router)
    with patched(auth_router, **fakes):
        yield TestClient(app)


def test_the_first_factor_sets_a_challenge_cookie_and_no_session():
    async def challenged(**_kwargs):
        return auth_services.LoginResult("totp_challenge", "challenge-token")

    class NoRedis:
        def get(self, _key):
            return None

        def delete(self, _key):
            pass

    with routed(verify_login_code=challenged, get_redis_client=NoRedis) as client:
        r = client.post(
            "/auth/email/verify", json={"email": "admin@example.org", "code": "123456"}
        )

    assert r.status_code == 200
    assert r.json() == {"email": "admin@example.org", "totp_required": True}
    assert "auth_totp_challenge" in r.cookies
    assert "auth_session" not in r.cookies
    set_cookie = r.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "Max-Age=600" in set_cookie


def test_the_second_factor_needs_the_challenge_cookie():
    with routed() as client:
        r = client.post("/auth/totp/verify", json={"code": "123456"})
    assert r.status_code == 401


def test_the_second_factor_wants_six_digits():
    with routed() as client:
        r = client.post("/auth/totp/verify", json={"code": "12345"})
        assert r.status_code == 422
        r = client.post("/auth/totp/verify", json={"code": "abcdef"})
        assert r.status_code == 422


def test_a_wrong_second_factor_keeps_the_challenge():
    async def wrong(**_kwargs):
        raise auth_totp.InvalidTotpCodeError()

    with routed(verify_totp_challenge=wrong) as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post("/auth/totp/verify", json={"code": "000000"})

    assert r.status_code == 400
    assert "auth_totp_challenge" not in r.headers.get("set-cookie", "")


def test_an_expired_second_factor_sends_the_visitor_back_to_the_start():
    async def expired(**_kwargs):
        raise auth_totp.TotpChallengeExpiredError()

    with routed(verify_totp_challenge=expired) as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post("/auth/totp/verify", json={"code": "000000"})

    assert r.status_code == 410
    assert 'auth_totp_challenge=""' in r.headers["set-cookie"]


def test_a_second_factor_nobody_can_read_is_the_operator_s_problem_not_a_wrong_code():
    async def unreadable(**_kwargs):
        raise SecretUnreadableError()

    with routed(verify_totp_challenge=unreadable) as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post("/auth/totp/verify", json={"code": "123456"})

    assert r.status_code == 503
    assert r.json()["detail"] == "totp_secret_unreadable"
    # The challenge is kept: nothing the visitor does can fix this.
    assert "auth_totp_challenge" not in r.headers.get("set-cookie", "")


def test_a_right_second_factor_swaps_the_challenge_for_a_session():
    seen = {}

    async def right(**kwargs):
        seen.update(kwargs)
        return "session-token"

    async def whoami(_token):
        return User(email="admin@example.test")

    with routed(verify_totp_challenge=right, get_user_from_token=whoami) as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post(
            "/auth/totp/verify",
            json={"code": " 123 456 "},
            headers={"origin": "http://testserver"},
        )

    assert r.status_code == 200
    assert r.json() == {"email": "admin@example.test"}
    assert seen["token"] == "challenge-token"
    assert seen["code"] == "123456"
    cookies = r.headers.get_list("set-cookie")
    assert any(c.startswith('auth_totp_challenge=""') for c in cookies)
    assert any(c.startswith("auth_session=session-token") for c in cookies)


def test_the_second_factor_refuses_a_cross_site_origin():
    with routed() as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post(
            "/auth/totp/verify",
            json={"code": "123456"},
            headers={"origin": "https://attacker.example"},
        )
    assert r.status_code == 403


def test_me_says_whether_the_authenticator_is_enrolled():
    user = User(email="admin@example.test", role="admin")

    async def whoami(_token):
        return user

    async def enrolled_yes(_user_id):
        return True

    with routed(get_user_from_token=whoami, has_confirmed_totp=enrolled_yes) as client:
        client.cookies.set("auth_session", "session-token")
        r = client.get("/auth/me")

    assert r.json() == {
        "user": {"email": "admin@example.test", "role": "admin", "totp_enabled": True}
    }


def test_logout_drops_a_half_finished_sign_in_too():
    with routed() as client:
        client.cookies.set("auth_totp_challenge", "challenge-token")
        r = client.post("/auth/logout")
    assert r.status_code == 204
    assert any(
        c.startswith('auth_totp_challenge=""') for c in r.headers.get_list("set-cookie")
    )


# Enrolment routes and the admin gate


class NoRedis:
    def get(self, _key):
        return None

    def incr(self, _key):
        return 1

    def expire(self, _key, _ttl):
        pass

    def delete(self, _key):
        pass


@contextlib.contextmanager
def signed_in(user, **fakes):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import backend.auth.router as auth_router
    from backend.auth.dependencies import require_user

    app = FastAPI()
    app.include_router(auth_router.router)
    app.dependency_overrides[require_user] = lambda: user
    with patched(auth_router, **{"get_redis_client": NoRedis, **fakes}):
        yield TestClient(app)


async def platform():
    from types import SimpleNamespace

    return SimpleNamespace(platform_name="compar:IA")


def test_only_admins_can_enrol():
    user = User(email="someone@example.org", role="user")
    with signed_in(user, get_app_settings=platform) as client:
        assert client.post("/auth/totp/setup", json={}).status_code == 403
        assert (
            client.post("/auth/totp/confirm", json={"code": "123456"}).status_code
            == 403
        )


def test_setup_hands_the_secret_over_once_and_uncached():
    admin = User(email="admin@example.org", role="admin")
    seen = {}

    async def start(user, code, platform_name):
        seen.update(code=code, platform_name=platform_name)
        return auth_totp.TotpSetup(
            secret="ABCDEFGH",
            otpauth_uri="otpauth://totp/x",
            qr_svg="data:image/svg+xml,",
        )

    with signed_in(admin, get_app_settings=platform, start_totp_setup=start) as client:
        r = client.post("/auth/totp/setup", json={})

    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert r.json()["secret"] == "ABCDEFGH"
    assert seen == {"code": None, "platform_name": "compar:IA"}


def test_changing_device_over_the_api_says_when_a_code_is_missing_or_wrong():
    admin = User(email="admin@example.org", role="admin")

    async def needs_code(*_args):
        raise auth_totp.TotpCodeRequiredError()

    async def wrong(*_args):
        raise auth_totp.InvalidTotpCodeError()

    with signed_in(admin, get_app_settings=platform, start_totp_setup=needs_code) as c:
        r = c.post("/auth/totp/setup", json={})
        assert r.status_code == 400
        assert r.json()["detail"] == "totp_code_required"

    with signed_in(admin, get_app_settings=platform, start_totp_setup=wrong) as c:
        r = c.post("/auth/totp/setup", json={"code": "000000"})
        assert r.status_code == 400


def test_confirm_passes_the_current_session_along_so_it_survives():
    admin = User(email="admin@example.org", role="admin")
    seen = {}

    async def confirm(user, code, keep_token):
        seen.update(code=code, keep_token=keep_token)

    with signed_in(admin, confirm_totp_setup=confirm) as client:
        client.cookies.set("auth_session", "session-token")
        r = client.post("/auth/totp/confirm", json={"code": "123456"})

    assert r.status_code == 204
    assert seen == {"code": "123456", "keep_token": "session-token"}


def test_confirm_without_a_pending_secret_is_a_conflict():
    admin = User(email="admin@example.org", role="admin")

    async def nothing_pending(*_args):
        raise auth_totp.TotpSetupMissingError()

    with signed_in(admin, confirm_totp_setup=nothing_pending) as client:
        r = client.post("/auth/totp/confirm", json={"code": "123456"})
    assert r.status_code == 409


def test_too_many_wrong_enrolment_codes_are_refused():
    admin = User(email="admin@example.org", role="admin")

    class Saturated(NoRedis):
        def get(self, _key):
            return "10"

    with signed_in(admin, get_redis_client=Saturated) as client:
        r = client.post("/auth/totp/confirm", json={"code": "123456"})
    assert r.status_code == 429


def test_enrolment_routes_answer_503_when_no_key_opens_the_secret():
    admin = User(email="admin@example.org", role="admin")
    counted = []

    class Counting(NoRedis):
        def incr(self, key):
            counted.append(key)
            return 1

    async def unreadable(*_args):
        raise SecretUnreadableError()

    with signed_in(
        admin,
        get_app_settings=platform,
        start_totp_setup=unreadable,
        get_redis_client=Counting,
    ) as client:
        r = client.post("/auth/totp/setup", json={"code": "123456"})
    assert r.status_code == 503
    assert r.json()["detail"] == "totp_secret_unreadable"

    with signed_in(
        admin, confirm_totp_setup=unreadable, get_redis_client=Counting
    ) as client:
        r = client.post("/auth/totp/confirm", json={"code": "123456"})
    assert r.status_code == 503
    assert r.json()["detail"] == "totp_secret_unreadable"
    # Not the admin's doing: it does not eat into their attempts.
    assert counted == []


def test_admin_routes_want_an_enrolled_authenticator():
    from fastapi import HTTPException
    from starlette.requests import Request

    import backend.auth.dependencies as dependencies

    admin = User(email="admin@example.org", role="admin")
    request = Request({"type": "http", "headers": [(b"cookie", b"auth_session=t")]})

    async def whoami(_token):
        return admin

    async def not_enrolled(_user_id):
        return False

    async def enrolled_yes(_user_id):
        return True

    with patched(
        dependencies, get_user_from_token=whoami, has_confirmed_totp=not_enrolled
    ):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(dependencies.require_admin(request))
    assert refused.value.status_code == 403
    assert refused.value.detail == "totp_setup_required"

    with patched(
        dependencies, get_user_from_token=whoami, has_confirmed_totp=enrolled_yes
    ):
        assert asyncio.run(dependencies.require_admin(request)) is admin


def test_a_plain_user_is_refused_before_the_authenticator_is_looked_at():
    from fastapi import HTTPException
    from starlette.requests import Request

    import backend.auth.dependencies as dependencies

    request = Request({"type": "http", "headers": [(b"cookie", b"auth_session=t")]})

    async def whoami(_token):
        return User(email="someone@example.org", role="user")

    async def never(_user_id):
        raise AssertionError("looked up the authenticator of a non-admin")

    with patched(dependencies, get_user_from_token=whoami, has_confirmed_totp=never):
        with pytest.raises(HTTPException) as refused:
            asyncio.run(dependencies.require_admin(request))
    assert refused.value.detail == "admin_required"


# Peer reset


def test_an_admin_cannot_reset_their_own_authenticator():
    import backend.admin.services as admin_services

    me = uuid.uuid4()
    with pytest.raises(admin_services.CannotResetOwnTotpError):
        asyncio.run(admin_services.reset_user_totp(me, me))


def test_resetting_a_peer_drops_the_authenticator_and_their_sessions():
    import backend.admin.services as admin_services

    peer = User(email="peer@example.org", role="admin")
    session = FakeSession(peer, [peer.id])

    with fake_session(session, admin_services):
        assert asyncio.run(admin_services.reset_user_totp(peer.id, uuid.uuid4()))

    deleted = {s.table.name for s in session.statements if s.is_delete}
    assert deleted == {"auth_totp", "auth_totp_challenge", "auth_invite_token"}
    [revocation] = updates_on(session.statements, "auth_session")
    assert revocation["revoked_at"] is not None
    assert session.commits == 1


def test_resetting_an_unenrolled_or_missing_peer_is_not_found():
    import backend.admin.services as admin_services

    peer = User(email="peer@example.org", role="admin")
    with fake_session(FakeSession(peer, []), admin_services):
        assert not asyncio.run(admin_services.reset_user_totp(peer.id, uuid.uuid4()))
    with fake_session(FakeSession(None), admin_services):
        assert not asyncio.run(admin_services.reset_user_totp(peer.id, uuid.uuid4()))


@contextlib.contextmanager
def admin_routed(admin, **fakes):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import backend.admin.router as admin_router
    from backend.auth.dependencies import require_admin

    app = FastAPI()
    app.include_router(admin_router.router)
    app.dependency_overrides[require_admin] = lambda: admin
    with patched(admin_router, **fakes):
        yield TestClient(app)


def test_the_reset_route_answers_once_the_service_has_done_its_work():
    admin = User(email="admin@example.org", role="admin")
    peer_id = uuid.uuid4()
    seen = {}

    async def reset(user_id, current_user_id):
        seen.update(user_id=user_id, current_user_id=current_user_id)
        return True

    with admin_routed(admin, reset_user_totp=reset) as client:
        r = client.delete(f"/admin/users/{peer_id}/totp")

    assert r.status_code == 204
    assert seen == {"user_id": peer_id, "current_user_id": admin.id}


def test_the_reset_route_maps_the_service_answers():
    import backend.admin.services as admin_services

    admin = User(email="admin@example.org", role="admin")

    async def own(*_args):
        raise admin_services.CannotResetOwnTotpError()

    async def missing(*_args):
        return False

    with admin_routed(admin, reset_user_totp=own) as client:
        assert client.delete(f"/admin/users/{admin.id}/totp").status_code == 400
    with admin_routed(admin, reset_user_totp=missing) as client:
        assert client.delete(f"/admin/users/{uuid.uuid4()}/totp").status_code == 404


def cli_reset_module():
    # The package re-exports the function under the module's name, so the
    # module itself has to be fetched by path.
    import importlib

    return importlib.import_module("utils.database.actions.reset_totp")


def test_the_cli_reset_needs_no_second_admin():
    cli_reset = cli_reset_module()

    admin = User(email="only@example.org", role="admin")
    session = FakeSession(None, [admin])

    with fake_session(session, cli_reset):
        asyncio.run(cli_reset.reset_totp(admin.email))

    deleted = {s.table.name for s in session.statements if s.is_delete}
    assert deleted == {"auth_totp", "auth_totp_challenge", "auth_invite_token"}
    [revocation] = updates_on(session.statements, "auth_session")
    assert revocation["revoked_at"] is not None
    assert session.commits == 1


def test_the_cli_reset_refuses_an_unknown_email():
    cli_reset = cli_reset_module()

    session = FakeSession(None, [])
    with fake_session(session, cli_reset):
        with pytest.raises(cli_reset.UserNotFoundError):
            asyncio.run(cli_reset.reset_totp("nobody@example.org"))
    assert session.commits == 0


def test_the_cli_reset_is_wired_into_comparia_cli():
    from utils.database.cli import cli_db

    assert "reset-totp" in cli_db


def test_demoting_an_admin_forgets_their_authenticator():
    import backend.admin.services as admin_services
    from utils.database.models.auth import UserUpsert

    class Count:
        def one(self):
            return 1

    async def _count():
        return Count()

    async def refresh(_user):
        pass

    admin = User(email="admin@example.org", role="admin")
    session = FakeSession(admin)
    session.exec = lambda _s: _count()
    session.refresh = refresh
    with fake_session(session, admin_services):
        with patched(admin_services, _user_public=_public):
            asyncio.run(
                admin_services.update_user(
                    admin.id, UserUpsert(email=admin.email, role="user")
                )
            )
    assert {s.table.name for s in session.statements if s.is_delete} == {
        "auth_totp",
        "auth_totp_challenge",
    }


def test_deleting_an_admin_closes_every_way_back_in():
    """A soft-deleted account can be revived by an invite or a manual add,
    so nothing from before may still open it: no session, no email code,
    no invite link, no authenticator."""
    import backend.admin.services as admin_services

    class Count:
        def one(self):
            return 1

    async def _count():
        return Count()

    admin = User(email="admin@example.org", role="admin")
    session = FakeSession(admin)
    session.exec = lambda _s: _count()
    with fake_session(session, admin_services):
        assert asyncio.run(admin_services.delete_user(admin.id, uuid.uuid4()))

    assert {s.table.name for s in session.statements if s.is_delete} == {
        "auth_totp",
        "auth_totp_challenge",
        "auth_invite_token",
    }
    [sessions] = updates_on(session.statements, "auth_session")
    assert sessions["revoked_at"] is not None
    [codes] = updates_on(session.statements, "auth_login_code")
    assert codes["used_at"] is not None
    assert session.commits == 1


def test_cancelling_an_invite_closes_every_way_back_in_too():
    import backend.admin.services as admin_services
    from utils.database.models.auth import InviteToken

    admin = User(email="admin@example.org", role="admin")
    invite = InviteToken(
        user_id=admin.id,
        invited_by=uuid.uuid4(),
        token_hash="x",
        expires_at=datetime.now() + timedelta(hours=1),
    )
    session = FakeSession(admin, [invite])

    async def delete(_obj):
        pass

    session.delete = delete
    with fake_session(session, admin_services):
        assert asyncio.run(admin_services.cancel_user_invite(admin.id))

    assert [
        u["revoked_at"] is not None
        for u in updates_on(session.statements, "auth_session")
    ] == [True]
    assert "auth_totp" in {s.table.name for s in session.statements if s.is_delete}


async def _public(_session, user):
    from utils.database.models.auth import UserPublic

    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at="",
        last_seen_at="",
        source="",
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
