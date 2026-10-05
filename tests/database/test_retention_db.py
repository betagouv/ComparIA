"""
The retention purge against a real PostgreSQL database.

Every rule is one SQL statement run in batches, so a fake session would only
prove that the statements were sent. These run when COMPARIA_TEST_DB_URI points
at a throwaway database with the migrations applied:

    createdb comparia_test
    COMPARIA_DB_URI=postgresql://localhost/comparia_test uv run alembic upgrade head
    COMPARIA_TEST_DB_URI=postgresql://localhost/comparia_test uv run pytest tests/database/test_retention_db.py

Each test empties the tables it seeds, on the way in and on the way out.
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_DB_URI = os.environ.get("COMPARIA_TEST_DB_URI", "")

os.environ.setdefault("COMPARIA_DB_URI", TEST_DB_URI or "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

import backend.auth.inactivity as inactivity  # noqa: E402
import utils.database.models  # noqa: E402,F401
import utils.database.retention as retention  # noqa: E402
from utils.database.retention import RetentionPeriods, purge_expired_data  # noqa: E402
from utils.database.session import _async_url  # noqa: E402

pytestmark = pytest.mark.skipif(not TEST_DB_URI, reason="COMPARIA_TEST_DB_URI not set")

NOW = datetime(2026, 9, 15, 12, 0)
PERIODS = RetentionPeriods()

TRUNCATE = text(
    "TRUNCATE prompt_check_result, user_message, turn, llm_message, comparison, "
    "auth_consent_log, anonymous_consent_log, auth_session, auth_login_code, "
    "auth_totp_challenge, auth_invite_token, auth_totp, legal_document, "
    "llm_data, llm_lab, llm_license, auth_user CASCADE"
)


def months_ago(months: int, days: int = 0) -> datetime:
    return retention.add_months(NOW, -months) - timedelta(days=days)


def run(scenario):
    """Run `scenario(execute)` with the purge bound to the test database.

    `execute` runs one SQL statement in its own transaction and returns the
    rows, if any.
    """

    async def main():
        engine = create_async_engine(_async_url(TEST_DB_URI))

        @contextlib.asynccontextmanager
        async def get_session():
            async with AsyncSession(engine) as session:
                yield session

        async def execute(sql, **params):
            async with engine.begin() as connection:
                result = await connection.execute(text(sql), params)
                return result.mappings().all() if result.returns_rows else None

        originals = retention.get_session, inactivity.get_session
        retention.get_session = inactivity.get_session = get_session
        try:
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await seed_catalogue(execute)
            return await scenario(execute)
        finally:
            retention.get_session, inactivity.get_session = originals
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await engine.dispose()

    return asyncio.run(main())


LLM_ID = uuid.uuid4()
DOCUMENT_ID = uuid.uuid4()


async def seed_catalogue(execute):
    """One model and one legal document, which comparisons and consents need."""
    lab_id, license_id = uuid.uuid4(), uuid.uuid4()
    await execute(
        "INSERT INTO llm_lab (id, created_at, updated_at, name, origin_country) "
        "VALUES (:id, now(), now(), 'Lab', 'FR')",
        id=lab_id,
    )
    await execute(
        "INSERT INTO llm_license (id, created_at, updated_at, kind, name, reuse, "
        "commercial_use) VALUES (:id, now(), now(), 'open', 'MIT', true, true)",
        id=license_id,
    )
    await execute(
        "INSERT INTO llm_data (id, created_at, updated_at, lab_id, license_id, "
        "human_id, status, name, rate_limited, release_date, arch, params, inputs, "
        "public_weights, public_training_data, public_training_code, eu_hostable, "
        "price_in, price_out, links) VALUES (:id, now(), now(), :lab, :license, "
        "'model', 'enabled', 'Model', false, :release, 'dense', 1, '[]', true, "
        "false, false, true, 0, 0, '[]')",
        id=LLM_ID,
        lab=lab_id,
        license=license_id,
        release=date(2025, 1, 1),
    )
    await execute(
        "INSERT INTO legal_document (id, kind, version, language, content, "
        "content_hash, published_at, effective_at) VALUES (:id, 'terms', '1', "
        "'fr', 'terms', :hash, now(), now())",
        id=DOCUMENT_ID,
        hash="0" * 64,
    )


async def add_user(execute, deleted_at=None):
    user_id = uuid.uuid4()
    await execute(
        "INSERT INTO auth_user (id, email, role, created_at, last_seen_at, "
        "deleted_at) VALUES (:id, :email, 'user', :now, :now, :deleted_at)",
        id=user_id,
        email=f"{user_id}@example.org",
        now=NOW,
        deleted_at=deleted_at,
    )
    return user_id


async def add_comparison(
    execute,
    created_at,
    user_id=None,
    ip="203.0.113.7",
    visitor_id="matomo-visitor",
    anonymous_user_hash="a" * 64,
    prompt="Bonjour, je m'appelle Camille",
    cohorts=None,
    contains_pii=None,
    archived_at=None,
):
    comparison_id, turn_id = uuid.uuid4(), uuid.uuid4()
    await execute(
        "INSERT INTO comparison (id, created_at, updated_at, ip, visitor_id, "
        "user_id, anonymous_user_hash, participation_terms_version, cohorts, "
        "contains_pii, archived_at, mode, revealed, llm_id_a, llm_id_b) VALUES "
        "(:id, :at, :at, :ip, :visitor, :user_id, :hash, '1', :cohorts, :pii, "
        ":archived_at, 'random', false, :llm, :llm)",
        id=comparison_id,
        at=created_at,
        ip=ip,
        visitor=visitor_id,
        user_id=user_id,
        hash=anonymous_user_hash,
        cohorts=cohorts,
        pii=contains_pii,
        archived_at=archived_at,
        llm=LLM_ID,
    )
    await execute(
        "INSERT INTO turn (id, created_at, updated_at, comparison_id, "
        "keyword_annotations_a, keyword_annotations_b) "
        "VALUES (:id, :at, :at, :comparison, '[]', '[]')",
        id=turn_id,
        at=created_at,
        comparison=comparison_id,
    )
    await execute(
        "INSERT INTO user_message (id, created_at, role, turn_id, content) "
        "VALUES (:id, :at, 'user', :turn, :content)",
        id=uuid.uuid4(),
        at=created_at,
        turn=turn_id,
        content=prompt,
    )
    return comparison_id, turn_id


async def add_answers(execute, turn_id):
    """Both model answers of a turn, which the turn points at."""
    message_ids = uuid.uuid4(), uuid.uuid4()
    for message_id in message_ids:
        await execute(
            "INSERT INTO llm_message (id, role, created_at, responded_at, "
            "updated_at, content, generation_id, tokens, is_cached) VALUES "
            "(:id, 'assistant', :at, :at, :at, 'Bonjour Camille', 'gen', 3, false)",
            id=message_id,
            at=NOW,
        )
    await execute(
        "UPDATE turn SET llm_msg_a_id = :a, llm_msg_b_id = :b WHERE id = :id",
        a=message_ids[0],
        b=message_ids[1],
        id=turn_id,
    )
    return message_ids


async def add_conversation(execute, created_at, **kwargs):
    """A comparison with a question, both answers and a moderation result."""
    comparison_id, turn_id = await add_comparison(execute, created_at, **kwargs)
    await add_answers(execute, turn_id)
    await add_prompt_check(execute, created_at, turn_id)
    return comparison_id


async def add_session(execute, user_id, expires_at, revoked_at=None):
    session_id = uuid.uuid4()
    await execute(
        "INSERT INTO auth_session (id, user_id, token_hash, created_at, "
        "expires_at, revoked_at, user_agent, ip) VALUES (:id, :user_id, :hash, "
        ":created, :expires, :revoked, 'Firefox', '203.0.113.8')",
        id=session_id,
        user_id=user_id,
        hash=uuid.uuid4().hex,
        created=expires_at - timedelta(days=30),
        expires=expires_at,
        revoked=revoked_at,
    )
    return session_id


async def add_consent(
    execute, user_id, consented_at, session_id=None, anonymous_id=None
):
    consent_id = uuid.uuid4()
    await execute(
        "INSERT INTO auth_consent_log (id, user_id, terms_version, "
        "auth_session_id, source_anonymous_consent_id, purpose, consented_at, ip) "
        "VALUES (:id, :user_id, '1', :session, :anonymous, "
        "'terms_and_participation', :at, '203.0.113.9')",
        id=consent_id,
        user_id=user_id,
        session=session_id,
        anonymous=anonymous_id,
        at=consented_at,
    )
    return consent_id


async def add_anonymous_consent(execute, consented_at):
    consent_id = uuid.uuid4()
    await execute(
        "INSERT INTO anonymous_consent_log (id, anonymous_user_hash, document_id, "
        "terms_version, document_hash, language, purpose, client_accepted_at, "
        "consented_at) VALUES (:id, :hash, :document, '1', :doc_hash, 'fr', "
        "'terms_and_participation', :at, :at)",
        id=consent_id,
        hash=uuid.uuid4().hex * 2,
        document=DOCUMENT_ID,
        doc_hash="0" * 64,
        at=consented_at,
    )
    return consent_id


async def add_prompt_check(execute, created_at, turn_id=None):
    check_id = uuid.uuid4()
    await execute(
        "INSERT INTO prompt_check_result (id, created_at, turn_id, decision, "
        "model, latency_ms, scores, triggered, user_proceeded) VALUES (:id, :at, "
        ":turn, 'warned', 'mistral-moderation-latest', 12, '{\"pii\": 0.9}', "
        "'{}', false)",
        id=check_id,
        at=created_at,
        turn=turn_id,
    )
    return check_id


async def comparison_row(execute, comparison_id):
    rows = await execute(
        "SELECT c.ip, c.visitor_id, c.user_id, c.anonymous_user_hash, "
        "c.updated_at, m.content FROM comparison c JOIN turn t ON "
        "t.comparison_id = c.id JOIN user_message m ON m.turn_id = t.id "
        "WHERE c.id = :id",
        id=comparison_id,
    )
    return rows[0]


async def ids(execute, table):
    return {row["id"] for row in await execute(f"SELECT id FROM {table}")}


def test_comparisons_lose_the_ip_then_the_identifiers():
    async def scenario(execute):
        user_id = await add_user(execute)
        recent, _ = await add_comparison(execute, months_ago(2), user_id)
        ip_due, _ = await add_comparison(execute, months_ago(3, days=1), user_id)
        all_due, _ = await add_comparison(execute, months_ago(24, days=1), user_id)
        anonymous_due, _ = await add_comparison(execute, months_ago(30))

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["comparison_ip"] == 3
        assert report.counts["comparison_identifiers"] == 2

        row = await comparison_row(execute, recent)
        assert row["ip"] == "203.0.113.7"
        assert row["visitor_id"] == "matomo-visitor"
        assert row["user_id"] == user_id

        row = await comparison_row(execute, ip_due)
        assert row["ip"] == "erased"
        assert row["visitor_id"] == "matomo-visitor"
        assert row["user_id"] == user_id
        assert row["anonymous_user_hash"] == "a" * 64

        for comparison_id in (all_due, anonymous_due):
            row = await comparison_row(execute, comparison_id)
            assert row["ip"] == "erased"
            assert row["visitor_id"] is None
            assert row["user_id"] is None
            assert row["anonymous_user_hash"] is None
            # The conversation itself stays for the datasets.
            assert row["content"] == "Bonjour, je m'appelle Camille"

        # The account outlives its old comparisons.
        assert user_id in await ids(execute, "auth_user")

    run(scenario)


def test_the_boundary_day_is_kept():
    async def scenario(execute):
        at_ip_cutoff, _ = await add_comparison(execute, months_ago(3))
        at_cutoff, _ = await add_comparison(execute, months_ago(24))

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["comparison_ip"] == 1
        assert report.counts["comparison_identifiers"] == 0
        assert (await comparison_row(execute, at_ip_cutoff))["ip"] == "203.0.113.7"
        assert (await comparison_row(execute, at_cutoff))["visitor_id"] is not None

    run(scenario)


def test_already_blank_comparisons_are_not_counted():
    async def scenario(execute):
        await add_comparison(
            execute,
            months_ago(30),
            ip="erased",
            visitor_id=None,
            anonymous_user_hash=None,
        )
        # Rows imported from the legacy schema can carry an empty address.
        empty, _ = await add_comparison(
            execute, months_ago(5), ip="", visitor_id=None, anonymous_user_hash=None
        )

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["comparison_identifiers"] == 0
        assert report.counts["comparison_ip"] == 1
        assert (await comparison_row(execute, empty))["ip"] == "erased"

    run(scenario)


def test_sessions_codes_and_challenges_go_a_year_after_they_stopped_working():
    async def scenario(execute):
        user_id = await add_user(execute)
        live = await add_session(execute, user_id, NOW + timedelta(days=10))
        expired_recently = await add_session(execute, user_id, months_ago(11))
        expired_long_ago = await add_session(execute, user_id, months_ago(13))
        # Revoked long ago, even though it would have expired later.
        revoked_long_ago = await add_session(
            execute, user_id, months_ago(11), revoked_at=months_ago(13)
        )
        # Revoked recently: still a trace the policy keeps.
        revoked_recently = await add_session(
            execute, user_id, months_ago(13), revoked_at=months_ago(11)
        )
        consent = await add_consent(
            execute, user_id, months_ago(14), session_id=expired_long_ago
        )
        kept_consent = await add_consent(
            execute, user_id, months_ago(11), session_id=expired_recently
        )

        for expires_at in (months_ago(13), months_ago(11)):
            await execute(
                "INSERT INTO auth_login_code (id, user_id, code_hash, created_at, "
                "expires_at) VALUES (:id, :user_id, 'hash', :at, :at)",
                id=uuid.uuid4(),
                user_id=user_id,
                at=expires_at,
            )
            await execute(
                "INSERT INTO auth_totp_challenge (id, user_id, token_hash, "
                "created_at, expires_at, attempts) VALUES (:id, :user_id, 'hash', "
                ":at, :at, 0)",
                id=uuid.uuid4(),
                user_id=user_id,
                at=expires_at,
            )

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["sessions"] == 2
        assert report.counts["consent_session_links"] == 1
        assert report.counts["login_codes"] == 1
        assert report.counts["totp_challenges"] == 1
        assert await ids(execute, "auth_session") == {
            live,
            expired_recently,
            revoked_recently,
        }
        assert revoked_long_ago not in await ids(execute, "auth_session")

        consents = {
            row["id"]: row["auth_session_id"]
            for row in await execute("SELECT id, auth_session_id FROM auth_consent_log")
        }
        # The proof stays, only its link to the deleted session goes.
        assert consents == {consent: None, kept_consent: expired_recently}

        for table in ("auth_login_code", "auth_totp_challenge"):
            rows = await execute(f"SELECT expires_at FROM {table}")
            assert [row["expires_at"] for row in rows] == [months_ago(11)]

    run(scenario)


def test_a_live_account_keeps_its_last_session_without_ip_or_browser():
    async def scenario(execute):
        dormant = await add_user(execute)
        older = await add_session(execute, dormant, months_ago(26))
        latest = await add_session(execute, dormant, months_ago(25))
        gone = await add_user(execute, deleted_at=months_ago(20))
        await add_session(execute, gone, months_ago(25))

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["sessions"] == 2
        assert report.counts["session_details"] == 1
        rows = await execute("SELECT id, ip, user_agent FROM auth_session")
        assert [(row["id"], row["ip"], row["user_agent"]) for row in rows] == [
            (latest, "erased", None)
        ]
        assert older not in await ids(execute, "auth_session")

        again = await purge_expired_data(PERIODS, apply=True, now=NOW)
        assert sum(again.counts.values()) == 0

    run(scenario)


def test_a_dormant_account_is_still_warned_after_the_purge():
    """purge-inactive erases accounts without any session row unwarned, as
    login codes nobody used. Old sessions going must not make a real account
    look like one."""

    async def scenario(execute):
        dormant = await add_user(execute)
        await execute(
            "UPDATE auth_user SET last_seen_at = :at WHERE id = :id",
            at=months_ago(25),
            id=dormant,
        )
        await add_session(execute, dormant, months_ago(25, days=-30))

        await purge_expired_data(PERIODS, apply=True, now=NOW)
        report = await inactivity.find_inactive_users(24, NOW)

        assert [user.id for user in report.to_warn] == [dormant]
        assert report.never_signed_in == []

    run(scenario)


def test_moderation_results_go_after_a_year():
    async def scenario(execute):
        _, turn_id = await add_comparison(execute, months_ago(2))
        kept = await add_prompt_check(execute, months_ago(11), turn_id)
        await add_prompt_check(execute, months_ago(13))
        await add_prompt_check(execute, months_ago(40))

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["prompt_check_results"] == 2
        assert await ids(execute, "prompt_check_result") == {kept}
        assert len(await ids(execute, "turn")) == 1

    run(scenario)


def test_consent_proofs_go_five_years_after_the_account_or_session_ended():
    async def scenario(execute):
        live_user = await add_user(execute)
        deleted_long_ago = await add_user(execute, deleted_at=months_ago(61))
        deleted_recently = await add_user(execute, deleted_at=months_ago(59))
        # Past five years by days: the anonymous grace period is not theirs.
        deleted_just_past = await add_user(execute, deleted_at=months_ago(60, days=10))

        anonymous_free = await add_anonymous_consent(execute, months_ago(62))
        anonymous_grace = await add_anonymous_consent(execute, months_ago(60, days=10))
        anonymous_recent = await add_anonymous_consent(execute, months_ago(12))
        anonymous_of_live = await add_anonymous_consent(execute, months_ago(70))
        anonymous_of_gone = await add_anonymous_consent(execute, months_ago(70))

        live_consent = await add_consent(
            execute, live_user, months_ago(70), anonymous_id=anonymous_of_live
        )
        await add_consent(
            execute, deleted_long_ago, months_ago(70), anonymous_id=anonymous_of_gone
        )
        recent_consent = await add_consent(execute, deleted_recently, months_ago(70))
        await add_consent(execute, deleted_just_past, months_ago(70))

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["account_consents"] == 2
        assert report.counts["anonymous_consents"] == 2
        assert await ids(execute, "auth_consent_log") == {live_consent, recent_consent}
        assert await ids(execute, "anonymous_consent_log") == {
            anonymous_grace,
            anonymous_recent,
            anonymous_of_live,
        }
        assert anonymous_free not in await ids(execute, "anonymous_consent_log")
        # The account rows themselves are left to purge-inactive.
        assert len(await ids(execute, "auth_user")) == 4

    run(scenario)


def test_dry_run_counts_without_changing_anything():
    async def scenario(execute):
        user_id = await add_user(execute)
        comparison_id, turn_id = await add_comparison(execute, months_ago(30), user_id)
        await add_session(execute, user_id, months_ago(13))
        await add_prompt_check(execute, months_ago(13), turn_id)

        dry = await purge_expired_data(PERIODS, apply=False, now=NOW)

        row = await comparison_row(execute, comparison_id)
        assert row["ip"] == "203.0.113.7"
        assert row["user_id"] == user_id
        assert len(await ids(execute, "auth_session")) == 1
        assert len(await ids(execute, "prompt_check_result")) == 1

        applied = await purge_expired_data(PERIODS, apply=True, now=NOW)
        assert dry.counts == applied.counts
        assert sum(applied.counts.values()) == 4

    run(scenario)


def test_runs_in_batches_and_a_second_run_finds_nothing(monkeypatch):
    monkeypatch.setattr(retention, "BATCH_SIZE", 2)

    async def scenario(execute):
        for _ in range(5):
            await add_comparison(execute, months_ago(30))
        for _ in range(4):
            await add_prompt_check(execute, months_ago(13))

        first = await purge_expired_data(PERIODS, apply=True, now=NOW)
        assert first.counts["comparison_identifiers"] == 5
        assert first.counts["comparison_ip"] == 5
        # An exact multiple of the batch size still ends.
        assert first.counts["prompt_check_results"] == 4

        rows = await execute(
            "SELECT count(*) AS n FROM comparison WHERE ip <> 'erased' "
            "OR visitor_id IS NOT NULL OR anonymous_user_hash IS NOT NULL"
        )
        assert rows[0]["n"] == 0

        second = await purge_expired_data(PERIODS, apply=True, now=NOW)
        assert sum(second.counts.values()) == 0

    run(scenario)


def test_each_rule_follows_its_own_period():
    """Every period differs, so a rule reading another rule's period fails."""
    periods = RetentionPeriods(
        ip_months=1,
        comparison_months=2,
        prompt_check_months=3,
        session_months=4,
        consent_years=1,
    )

    async def scenario(execute):
        ip_only, _ = await add_comparison(execute, months_ago(1, days=1))
        both, _ = await add_comparison(execute, months_ago(2, days=1))
        kept_check = await add_prompt_check(execute, months_ago(2, days=20))
        await add_prompt_check(execute, months_ago(3, days=1))
        user_id = await add_user(execute)
        kept_session = await add_session(execute, user_id, months_ago(3, days=1))
        await add_session(execute, user_id, months_ago(4, days=1))
        gone_user = await add_user(execute, deleted_at=months_ago(12, days=1))
        await add_consent(execute, gone_user, months_ago(20))
        kept_user = await add_user(execute, deleted_at=months_ago(4, days=1))
        kept_consent = await add_consent(execute, kept_user, months_ago(20))

        report = await purge_expired_data(periods, apply=True, now=NOW)

        assert report.counts["comparison_ip"] == 2
        assert report.counts["comparison_identifiers"] == 1
        row = await comparison_row(execute, ip_only)
        assert (row["ip"], row["visitor_id"]) == ("erased", "matomo-visitor")
        row = await comparison_row(execute, both)
        assert (row["ip"], row["visitor_id"]) == ("erased", None)
        assert await ids(execute, "prompt_check_result") == {kept_check}
        assert await ids(execute, "auth_session") == {kept_session}
        assert await ids(execute, "auth_consent_log") == {kept_consent}

    run(scenario)


async def conversation_counts(execute):
    return {
        table: len(await ids(execute, table))
        for table in (
            "comparison",
            "turn",
            "user_message",
            "llm_message",
            "prompt_check_result",
        )
    }


def test_conversations_flagged_as_personal_go_30_days_after_the_analysis(
    monkeypatch,
):
    monkeypatch.setattr(retention, "CONVERSATION_BATCH_SIZE", 2)

    async def scenario(execute):
        for _ in range(4):
            await add_conversation(
                execute,
                NOW - timedelta(days=40),
                contains_pii=True,
                archived_at=NOW - timedelta(days=31),
            )
        # Flagged long after it was written: the clock starts at the analysis.
        recent_flag = await add_conversation(
            execute,
            months_ago(6),
            contains_pii=True,
            archived_at=NOW - timedelta(days=29),
        )
        # Imported from the legacy schema, without an analysis date.
        await add_conversation(execute, months_ago(6), contains_pii=True)
        clean = await add_conversation(execute, months_ago(6), contains_pii=False)

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["pii_conversations"] == 5
        assert await ids(execute, "comparison") == {recent_flag, clean}
        assert await conversation_counts(execute) == {
            "comparison": 2,
            "turn": 2,
            "user_message": 2,
            "llm_message": 4,
            "prompt_check_result": 2,
        }

        again = await purge_expired_data(PERIODS, apply=True, now=NOW)
        assert again.counts["pii_conversations"] == 0

    run(scenario)


def test_partner_cohort_conversations_go_after_30_days():
    async def scenario(execute):
        await add_conversation(execute, NOW - timedelta(days=31), cohorts="pix")
        pupil_recent = await add_conversation(
            execute, NOW - timedelta(days=29), cohorts="pix"
        )
        no_cohort = await add_conversation(execute, months_ago(6), cohorts="")
        untagged = await add_conversation(execute, months_ago(6))

        dry = await purge_expired_data(PERIODS, apply=False, now=NOW)
        assert dry.counts["cohort_conversations"] == 1
        assert len(await ids(execute, "comparison")) == 4

        report = await purge_expired_data(PERIODS, apply=True, now=NOW)

        assert report.counts["cohort_conversations"] == 1
        assert await ids(execute, "comparison") == {
            pupil_recent,
            no_cohort,
            untagged,
        }
        assert (await conversation_counts(execute))["llm_message"] == 6

    run(scenario)
