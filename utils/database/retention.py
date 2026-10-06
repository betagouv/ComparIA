"""Retention periods from the privacy policy, applied to the tables.

Accounts are handled by backend/auth/inactivity.py, which has to warn people
before it erases anything. Everything here goes without notice: it either
blanks the columns that point back at someone, deletes rows that only
existed to trace a session or a check, or deletes whole conversations that
will never be published.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import ColumnElement, CursorResult, Delete, Update, and_
from sqlalchemy import delete as sa_delete
from sqlalchemy import exists, func, or_
from sqlalchemy import update as sa_update
from sqlalchemy.orm import aliased
from sqlmodel import col, select

from backend.auth.inactivity import add_months
from backend.auth.services import ERASED_IP
from backend.config import settings
from utils.database.models.auth import (
    AnonymousConsentLog,
    AuthSession,
    ConsentLog,
    LoginCode,
    TotpChallenge,
    User,
)
from utils.database.models.comparison import Comparison
from utils.database.models.messages import LLMMessage, UserMessage
from utils.database.models.prompt_check import PromptCheckResult
from utils.database.models.turn import Turn
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")

# Rows touched per transaction. The comparison table holds millions of rows
# and the arena keeps writing to it: small batches keep each lock short.
BATCH_SIZE = 5000
# A conversation brings its turns and messages along, and the ids of a batch
# travel as query parameters: smaller batches stay far below the driver's
# limit on parameters.
CONVERSATION_BATCH_SIZE = 200


@dataclass
class RetentionPeriods:
    # comparison.ip. Nothing in the app reads it back; the rate limits keep
    # their own copy in Redis for an hour.
    ip_months: int = 3
    # user_id, visitor_id and anonymous_user_hash on a comparison. The text
    # stays, cut off from whoever wrote it.
    comparison_months: int = 24
    # Session rows, login codes and 2FA challenges, counted from the moment
    # they stopped working.
    session_months: int = 12
    # Moderation results, which hold the scores the check gave a prompt.
    prompt_check_months: int = 12
    # Proof that the terms were accepted, counted from the account's
    # deletion, or from the end of the anonymous session for a visitor.
    consent_years: int = 5
    # Conversations the analysis flagged as holding personal data. They are
    # never published nor counted in the ranking. Counted from the analysis.
    pii_days: int = 30
    # Conversations that came through a partner programme, Pix pupils for
    # now. They are never published nor counted in the ranking; only the
    # person's own history shows them.
    cohort_days: int = 30


@dataclass
class RetentionReport:
    counts: dict[str, int] = field(default_factory=dict)


@dataclass
class _Rule:
    name: str
    # A table model: SQLModel classes share no type that declares `id`.
    table: Any
    where: ColumnElement[bool]
    # None deletes the matching rows, otherwise the columns to overwrite.
    values: dict | None = None
    # Delete the matching comparisons with their turns and messages.
    whole_conversations: bool = False


def _rules(periods: RetentionPeriods, now: datetime) -> list[_Rule]:
    ip_cutoff = add_months(now, -periods.ip_months)
    comparison_cutoff = add_months(now, -periods.comparison_months)
    session_cutoff = add_months(now, -periods.session_months)
    prompt_check_cutoff = add_months(now, -periods.prompt_check_months)
    consent_cutoff = add_months(now, -12 * periods.consent_years)
    pii_cutoff = now - timedelta(days=periods.pii_days)
    cohort_cutoff = now - timedelta(days=periods.cohort_days)
    # An anonymous session cannot outlive its cookie, which is never renewed,
    # so its last use is at most that long after the consent.
    anonymous_consent_cutoff = consent_cutoff - timedelta(
        days=settings.ANONYMOUS_SESSION_LENGTH_DAYS
    )

    session_ended = func.coalesce(
        col(AuthSession.revoked_at), col(AuthSession.expires_at)
    )
    # purge-inactive tells a dormant account from a login code nobody used by
    # whether it has a session row, and only warns the former. A live
    # account's latest session therefore stays, stripped of its IP and
    # browser, so the account still gets its warning before it is erased.
    newer = aliased(AuthSession)
    session_gone = and_(
        session_ended < session_cutoff,
        or_(
            exists().where(
                col(newer.user_id) == col(AuthSession.user_id),
                col(newer.created_at) > col(AuthSession.created_at),
            ),
            exists().where(
                col(User.id) == col(AuthSession.user_id),
                col(User.deleted_at).is_not(None),
            ),
        ),
    )

    return [
        # First, so the rules below do not blank rows about to go.
        _Rule(
            "pii_conversations",
            Comparison,
            and_(
                col(Comparison.contains_pii).is_(True),
                # The analysis sets archived_at; rows imported from the
                # legacy schema may lack it.
                func.coalesce(col(Comparison.archived_at), col(Comparison.created_at))
                < pii_cutoff,
            ),
            whole_conversations=True,
        ),
        _Rule(
            "cohort_conversations",
            Comparison,
            and_(
                col(Comparison.cohorts).is_not(None),
                col(Comparison.cohorts) != "",
                col(Comparison.created_at) < cohort_cutoff,
            ),
            whole_conversations=True,
        ),
        _Rule(
            "comparison_identifiers",
            Comparison,
            and_(
                col(Comparison.created_at) < comparison_cutoff,
                or_(
                    col(Comparison.user_id).is_not(None),
                    col(Comparison.visitor_id).is_not(None),
                    col(Comparison.anonymous_user_hash).is_not(None),
                ),
            ),
            {"user_id": None, "visitor_id": None, "anonymous_user_hash": None},
        ),
        _Rule(
            "comparison_ip",
            Comparison,
            and_(
                col(Comparison.created_at) < ip_cutoff,
                col(Comparison.ip) != ERASED_IP,
            ),
            {"ip": ERASED_IP},
        ),
        _Rule(
            "prompt_check_results",
            PromptCheckResult,
            col(PromptCheckResult.created_at) < prompt_check_cutoff,
        ),
        # A consent proof may name the session it was given in. The proof
        # outlives the session by years, so the link goes first.
        _Rule(
            "consent_session_links",
            ConsentLog,
            col(ConsentLog.auth_session_id).in_(
                select(col(AuthSession.id)).where(session_gone)
            ),
            {"auth_session_id": None},
        ),
        _Rule("sessions", AuthSession, session_gone),
        _Rule(
            "session_details",
            AuthSession,
            and_(
                session_ended < session_cutoff,
                or_(
                    col(AuthSession.ip) != ERASED_IP,
                    col(AuthSession.user_agent).is_not(None),
                ),
            ),
            {"ip": ERASED_IP, "user_agent": None},
        ),
        _Rule("login_codes", LoginCode, col(LoginCode.expires_at) < session_cutoff),
        _Rule(
            "totp_challenges",
            TotpChallenge,
            col(TotpChallenge.expires_at) < session_cutoff,
        ),
        _Rule(
            "account_consents",
            ConsentLog,
            col(ConsentLog.user_id).in_(
                select(col(User.id)).where(col(User.deleted_at) < consent_cutoff)
            ),
        ),
        # Kept while an account's proof points at it: signing in copies the
        # visitor's consent onto the account, and the account's own clock
        # applies from then on.
        _Rule(
            "anonymous_consents",
            AnonymousConsentLog,
            and_(
                col(AnonymousConsentLog.consented_at) < anonymous_consent_cutoff,
                ~exists().where(
                    col(ConsentLog.source_anonymous_consent_id)
                    == col(AnonymousConsentLog.id)
                ),
            ),
        ),
    ]


async def _count(rule: _Rule) -> int:
    async with get_session() as session:
        result = await session.exec(
            select(func.count()).select_from(rule.table).where(rule.where)
        )
        return result.one()


async def _apply(rule: _Rule) -> int:
    """Run the rule in batches, each in its own transaction, until no row
    matches. A batch only picks rows that still match, so a run that stops
    halfway leaves nothing half done and the next one carries on."""
    if rule.whole_conversations:
        return await _delete_conversations(rule)
    total = 0
    while True:
        batch = select(rule.table.id).where(rule.where).limit(BATCH_SIZE)
        statement: Delete | Update = (
            sa_delete(rule.table).where(rule.table.id.in_(batch))
            if rule.values is None
            else sa_update(rule.table)
            .where(rule.table.id.in_(batch))
            .values(**rule.values)
        )
        async with get_session() as session:
            result = cast(CursorResult, await session.execute(statement))
            await session.commit()
        total += result.rowcount
        if result.rowcount < BATCH_SIZE:
            return total


async def _delete_conversations(rule: _Rule) -> int:
    """Delete the comparisons the rule matches, in batches like _apply. The
    foreign keys carry no ON DELETE CASCADE: what points at a turn goes
    first, then the turns, then the model messages they pointed at."""
    total = 0
    while True:
        async with get_session() as session:
            comparison_ids = (
                await session.exec(
                    select(col(Comparison.id))
                    .where(rule.where)
                    .limit(CONVERSATION_BATCH_SIZE)
                )
            ).all()
            turns = (
                await session.exec(
                    select(
                        col(Turn.id), col(Turn.llm_msg_a_id), col(Turn.llm_msg_b_id)
                    ).where(col(Turn.comparison_id).in_(comparison_ids))
                )
            ).all()
            turn_ids = [turn_id for turn_id, _, _ in turns]
            message_ids = [
                message_id
                for _, msg_a, msg_b in turns
                for message_id in (msg_a, msg_b)
                if message_id is not None
            ]
            for statement in (
                sa_delete(PromptCheckResult).where(
                    col(PromptCheckResult.turn_id).in_(turn_ids)
                ),
                sa_delete(UserMessage).where(col(UserMessage.turn_id).in_(turn_ids)),
                sa_delete(Turn).where(col(Turn.id).in_(turn_ids)),
                sa_delete(LLMMessage).where(col(LLMMessage.id).in_(message_ids)),
                sa_delete(Comparison).where(col(Comparison.id).in_(comparison_ids)),
            ):
                await session.execute(statement)
            await session.commit()
        total += len(comparison_ids)
        if len(comparison_ids) < CONVERSATION_BATCH_SIZE:
            return total


async def purge_expired_data(
    periods: RetentionPeriods,
    apply: bool = False,
    now: datetime | None = None,
) -> RetentionReport:
    now = now or datetime.now()
    report = RetentionReport()
    for rule in _rules(periods, now):
        report.counts[rule.name] = await (_apply(rule) if apply else _count(rule))
    return report
