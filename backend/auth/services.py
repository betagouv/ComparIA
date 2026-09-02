import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlmodel import select

from backend.config import settings
from backend.settings.legal import DEFAULT_LEGAL_LANGUAGE, get_active_legal_document
from utils.database.models.auth import (
    AnonymousConsentLog,
    AuthSession,
    ConsentLog,
    InviteToken,
    LegalDocument,
    LoginCode,
    User,
)
from utils.database.models.comparison import (
    LEGACY_PARTICIPATION_TERMS_VERSION,
    Comparison,
)
from utils.database.models.utils import as_naive_utc, utc_now
from utils.database.session import get_session

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger("languia")

_LOGIN_CODE_TTL_MINUTES = 10
_INVITE_TOKEN_TTL_HOURS = 24


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


async def request_login_code(email: str) -> str:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            user = User(email=email)
            session.add(user)
            await session.flush()

        await session.execute(
            sa_update(LoginCode)
            .where(LoginCode.user_id == user.id, LoginCode.used_at.is_(None))
            .values(used_at=datetime.now())
        )

        code = f"{secrets.randbelow(10**6):06d}"
        session.add(
            LoginCode(
                user_id=user.id,
                code_hash=_hash(code),
                expires_at=datetime.now() + timedelta(minutes=_LOGIN_CODE_TTL_MINUTES),
            )
        )
        await session.commit()

    return code


async def _create_session(
    session: "AsyncSession",
    user: User,
    ip: str,
    user_agent: str | None,
    visitor_id: str | None,
    anonymous_user_hash: str | None = None,
) -> str:
    """Create the AuthSession for a user that just authenticated (login code or
    invite link), carry over the acceptance they gave while anonymous, and
    reattach their anonymous comparisons. Logging in is not an acceptance in
    itself. Does not commit; caller owns the transaction."""
    user.last_seen_at = datetime.now()

    token = secrets.token_urlsafe(32)
    auth_session = AuthSession(
        user_id=user.id,
        token_hash=_hash(token),
        expires_at=datetime.now() + timedelta(days=settings.AUTH_SESSION_LENGTH_DAYS),
        ip=ip,
        user_agent=user_agent,
    )
    session.add(auth_session)

    if anonymous_user_hash:
        await _associate_anonymous_acceptance(
            session, user, auth_session, anonymous_user_hash
        )

    if visitor_id:
        await session.execute(
            sa_update(Comparison)
            .where(
                Comparison.visitor_id == visitor_id,
                Comparison.user_id.is_(None),
            )
            .values(user_id=user.id)
        )

    return token


async def _associate_anonymous_acceptance(
    session: "AsyncSession",
    user: User,
    auth_session: AuthSession,
    anonymous_user_hash: str,
) -> None:
    """Copy the visitor's own acceptance onto the account they just signed into,
    keeping the original acceptance time rather than asking them again."""
    result = await session.exec(
        select(AnonymousConsentLog)
        .where(AnonymousConsentLog.anonymous_user_hash == anonymous_user_hash)
        .order_by(AnonymousConsentLog.consented_at.desc())
    )
    acceptance = result.first()
    if not acceptance:
        return

    existing = await session.exec(
        select(ConsentLog).where(
            ConsentLog.user_id == user.id,
            ConsentLog.source_anonymous_consent_id == acceptance.id,
        )
    )
    if existing.first():
        return

    session.add(
        ConsentLog(
            user_id=user.id,
            auth_session_id=auth_session.id,
            source_anonymous_consent_id=acceptance.id,
            terms_version=acceptance.terms_version,
            document_id=acceptance.document_id,
            document_hash=acceptance.document_hash,
            language=acceptance.language,
            purpose=acceptance.purpose,
            client_accepted_at=acceptance.client_accepted_at,
            consented_at=acceptance.consented_at,
            associated_at=utc_now(),
            ip="not_collected",
        )
    )


async def verify_login_code(
    email: str,
    code: str,
    ip: str,
    user_agent: str | None,
    visitor_id: str | None,
    anonymous_user_hash: str | None = None,
) -> str | None:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            return None

        result = await session.exec(
            select(LoginCode).where(
                LoginCode.user_id == user.id,
                LoginCode.code_hash == _hash(code),
                LoginCode.used_at.is_(None),
                LoginCode.expires_at > datetime.now(),
            )
        )
        login_code = result.first()
        if not login_code:
            return None

        login_code.used_at = datetime.now()

        token = await _create_session(
            session, user, ip, user_agent, visitor_id, anonymous_user_hash
        )

        await session.commit()

    return token


async def create_invite(email: str, invited_by: uuid.UUID) -> str:
    async with get_session() as session:
        result = await session.exec(select(User).where(User.email == email))
        user = result.first()
        if not user:
            user = User(email=email)
            session.add(user)
            await session.flush()
        elif user.deleted_at is not None:
            # Email is unique, so re-inviting a deleted user must revive
            # their existing row rather than leave it permanently dead.
            # Clear their old auth history too, otherwise a previously
            # accepted invite or used login code makes list_users report
            # them as already joined instead of pending on the new invite.
            user.deleted_at = None
            session.add(user)

            old_invites = await session.exec(
                select(InviteToken).where(InviteToken.user_id == user.id)
            )
            for invite in old_invites.all():
                await session.delete(invite)

            old_codes = await session.exec(
                select(LoginCode).where(LoginCode.user_id == user.id)
            )
            for login_code in old_codes.all():
                await session.delete(login_code)

        token = secrets.token_urlsafe(32)
        session.add(
            InviteToken(
                user_id=user.id,
                invited_by=invited_by,
                token_hash=_hash(token),
                expires_at=datetime.now() + timedelta(hours=_INVITE_TOKEN_TTL_HOURS),
            )
        )
        await session.commit()

    return token


@dataclass
class InviteTokenInfo:
    email: str


async def get_invite_token_info(token: str) -> InviteTokenInfo | None:
    """Read-only check used by the frontend to show an error before the user
    even fills in the consent form. Does not mark the token as used — the
    actual accept_invite() call re-validates everything regardless."""
    async with get_session() as session:
        result = await session.exec(
            select(InviteToken).where(
                InviteToken.token_hash == _hash(token),
                InviteToken.used_at.is_(None),
                InviteToken.expires_at > datetime.now(),
            )
        )
        invite = result.first()
        if not invite:
            return None

        user = await session.get(User, invite.user_id)
        if not user or user.deleted_at is not None:
            return None

        return InviteTokenInfo(email=user.email)


async def accept_invite(
    token: str,
    ip: str,
    user_agent: str | None,
    visitor_id: str | None,
    anonymous_user_hash: str | None = None,
) -> str | None:
    async with get_session() as session:
        result = await session.exec(
            select(InviteToken).where(
                InviteToken.token_hash == _hash(token),
                InviteToken.used_at.is_(None),
                InviteToken.expires_at > datetime.now(),
            )
        )
        invite = result.first()
        if not invite:
            return None

        user = await session.get(User, invite.user_id)
        if not user or user.deleted_at is not None:
            return None

        invite.used_at = datetime.now()

        session_token = await _create_session(
            session, user, ip, user_agent, visitor_id, anonymous_user_hash
        )

        await session.commit()

    return session_token


async def get_user_from_token(token: str) -> User | None:
    async with get_session() as session:
        result = await session.exec(
            select(AuthSession).where(
                AuthSession.token_hash == _hash(token),
                AuthSession.expires_at > datetime.now(),
                AuthSession.revoked_at.is_(None),
            )
        )
        auth_session = result.first()
        if not auth_session:
            return None

        user = await session.get(User, auth_session.user_id)
        if not user or user.deleted_at is not None:
            return None

        return user


async def revoke_current_session(token: str) -> None:
    async with get_session() as session:
        result = await session.exec(
            select(AuthSession).where(AuthSession.token_hash == _hash(token))
        )
        auth_session = result.first()
        if auth_session:
            auth_session.revoked_at = datetime.now()
            session.add(auth_session)
            await session.commit()


async def revoke_all_user_sessions(user_id: uuid.UUID) -> None:
    async with get_session() as session:
        await session.execute(
            sa_update(AuthSession)
            .where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now())
        )
        await session.commit()


async def record_user_consent(
    user_id: uuid.UUID,
    document: LegalDocument,
    accepted_at: datetime,
    auth_session_token: str | None,
) -> None:
    async with get_session() as session:
        auth_session_id = None
        if auth_session_token:
            result = await session.exec(
                select(AuthSession).where(
                    AuthSession.token_hash == _hash(auth_session_token),
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                )
            )
            auth_session = result.first()
            auth_session_id = auth_session.id if auth_session else None

        session.add(
            ConsentLog(
                user_id=user_id,
                auth_session_id=auth_session_id,
                document_id=document.id,
                terms_version=document.version,
                document_hash=document.content_hash,
                language=document.language,
                client_accepted_at=as_naive_utc(accepted_at),
                ip="not_collected",
            )
        )
        await session.commit()


async def record_anonymous_consent(
    anonymous_user_hash: str,
    document: LegalDocument,
    accepted_at: datetime,
) -> None:
    async with get_session() as session:
        session.add(
            AnonymousConsentLog(
                anonymous_user_hash=anonymous_user_hash,
                document_id=document.id,
                terms_version=document.version,
                document_hash=document.content_hash,
                language=document.language,
                client_accepted_at=as_naive_utc(accepted_at),
            )
        )
        await session.commit()


async def _latest_terms_consent(
    user_id: uuid.UUID | None, anonymous_user_hash: str | None
) -> ConsentLog | AnonymousConsentLog | None:
    async with get_session() as session:
        if user_id:
            # Rows written before versioned documents have no document to
            # compare against, so they cannot answer either question.
            result = await session.exec(
                select(ConsentLog)
                .where(
                    ConsentLog.user_id == user_id,
                    ConsentLog.document_id.is_not(None),
                )
                .order_by(ConsentLog.consented_at.desc())
            )
        else:
            result = await session.exec(
                select(AnonymousConsentLog)
                .where(AnonymousConsentLog.anonymous_user_hash == anonymous_user_hash)
                .order_by(AnonymousConsentLog.consented_at.desc())
            )
        return result.first()


def _terms_status(record: ConsentLog | AnonymousConsentLog | None) -> dict:
    if not record:
        return {"terms": None}
    return {
        "terms": {
            "version": record.terms_version,
            "content_hash": record.document_hash,
            "locale": record.language,
            "accepted_at": record.consented_at,
        }
    }


async def get_consent_status(user_id: uuid.UUID) -> dict:
    return _terms_status(await _latest_terms_consent(user_id, None))


async def get_anonymous_consent_status(anonymous_user_hash: str) -> dict:
    return _terms_status(await _latest_terms_consent(None, anonymous_user_hash))


async def get_current_terms_acceptance_version(
    *, user_id: uuid.UUID | None, anonymous_user_hash: str
) -> str | None:
    """Version of the terms in force that this visitor has accepted, if any.

    Returns the legacy marker when nothing is published: there is then nothing
    to accept, and gating on it would lock everyone out, including the
    administrator who has to publish the missing document.
    """
    record = await _latest_terms_consent(user_id, anonymous_user_hash)
    if record:
        document = await get_active_legal_document("terms", record.language)
        if document and record.document_id == document.id:
            return document.version
    # "Is anything published" is answered in the default language only. Retiring
    # the French terms while another language stays published would open the
    # gate for everyone. Only French is seeded today.
    if not await get_active_legal_document("terms", DEFAULT_LEGAL_LANGUAGE):
        return LEGACY_PARTICIPATION_TERMS_VERSION
    return None


async def has_current_terms_acceptance(
    *, user_id: uuid.UUID | None, anonymous_user_hash: str
) -> bool:
    return (
        await get_current_terms_acceptance_version(
            user_id=user_id, anonymous_user_hash=anonymous_user_hash
        )
        is not None
    )


ERASED_IP = "erased"


async def erase_user_account(user_id: uuid.UUID) -> None:
    """Cut every link between a person and what they left behind.

    The conversations stay, because they are published in the research
    datasets under the terms accepted when they were held. What goes is
    everything that points back at someone: the account address, the session
    trail, and the three identifiers each comparison carries. The acceptance
    proof survives without its address, since it is the record of a legal
    obligation rather than a trace of the person.
    """
    now = datetime.now()
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return

        await session.execute(
            sa_update(AuthSession)
            .where(AuthSession.user_id == user_id)
            .values(revoked_at=now, ip=ERASED_IP, user_agent=None)
        )
        await session.execute(
            sa_update(ConsentLog)
            .where(ConsentLog.user_id == user_id)
            .values(ip=ERASED_IP)
        )
        await session.execute(
            sa_update(Comparison)
            .where(Comparison.user_id == user_id)
            .values(
                user_id=None,
                ip=ERASED_IP,
                visitor_id=None,
                anonymous_user_hash=None,
            )
        )
        await session.execute(sa_delete(LoginCode).where(LoginCode.user_id == user_id))
        await session.execute(
            sa_delete(InviteToken).where(InviteToken.user_id == user_id)
        )

        # The row itself stays: the consent logs point at it, and it is what
        # stops a new sign-in from reviving the erased account.
        user.email = f"deleted-{user.id}@deleted.invalid"
        user.deleted_at = now
        session.add(user)
        await session.commit()
