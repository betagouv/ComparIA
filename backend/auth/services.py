import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol

from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlmodel import select

from backend.config import settings
from utils.database.models.auth import (
    AnonymousConsentLog,
    AuthSession,
    ConsentLog,
    InviteToken,
    LegalDocument,
    LoginCode,
    User,
)
from utils.database.models.comparison import Comparison
from utils.database.session import get_session

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger("languia")

_LOGIN_CODE_TTL_MINUTES = 10
_INVITE_TOKEN_TTL_HOURS = 24
_DEV_ANONYMOUS_CONSENTS: dict[str, dict] = {}


class ConsentAssertionValue(Protocol):
    accepted_at: datetime
    locale: str


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
    """Create an authenticated session without inferring any legal acceptance."""
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
    """Link the visitor's original proof to the account without re-consenting."""
    result = await session.exec(
        select(AnonymousConsentLog)
        .where(
            AnonymousConsentLog.anonymous_user_hash == anonymous_user_hash,
            AnonymousConsentLog.purpose == "terms_and_participation",
        )
        .order_by(AnonymousConsentLog.consented_at.desc())
    )
    anonymous_acceptance = result.first()
    if not anonymous_acceptance:
        return

    existing_result = await session.exec(
        select(ConsentLog).where(
            ConsentLog.user_id == user.id,
            ConsentLog.source_anonymous_consent_id == anonymous_acceptance.id,
        )
    )
    if existing_result.first():
        return

    session.add(
        ConsentLog(
            user_id=user.id,
            auth_session_id=auth_session.id,
            source_anonymous_consent_id=anonymous_acceptance.id,
            terms_version=anonymous_acceptance.terms_version,
            document_id=anonymous_acceptance.document_id,
            document_hash=anonymous_acceptance.document_hash,
            language=anonymous_acceptance.language,
            purpose=anonymous_acceptance.purpose,
            client_accepted_at=anonymous_acceptance.client_accepted_at,
            consented_at=anonymous_acceptance.consented_at,
            associated_at=datetime.now(),
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


async def get_consent_status(user_id: uuid.UUID) -> dict:
    async with get_session() as session:
        result = await session.exec(
            select(ConsentLog)
            .where(ConsentLog.user_id == user_id)
            .order_by(ConsentLog.consented_at.desc())
        )
        records = result.all()

    def latest(purpose: str) -> ConsentLog | None:
        return next((record for record in records if record.purpose == purpose), None)

    terms = latest("terms_and_participation")
    return {
        "terms": (
            None
            if not terms
            else {
                "version": terms.terms_version,
                "content_hash": terms.document_hash,
                "locale": terms.language,
                "accepted_at": terms.consented_at,
            }
        ),
    }


async def record_user_consent(
    user_id: uuid.UUID,
    consent: ConsentAssertionValue,
    document: LegalDocument,
    auth_session_token: str | None,
) -> None:
    """Append authenticated evidence only after an explicit arena assertion."""
    from backend.settings.legal import legal_document_public_hash

    if not settings.COMPARIA_DB_URI:
        return
    accepted_at = consent.accepted_at.replace(tzinfo=None)
    async with get_session() as session:
        auth_session_id = None
        if auth_session_token:
            session_result = await session.exec(
                select(AuthSession).where(
                    AuthSession.token_hash == _hash(auth_session_token),
                    AuthSession.user_id == user_id,
                    AuthSession.revoked_at.is_(None),
                )
            )
            auth_session = session_result.first()
            auth_session_id = auth_session.id if auth_session else None
        session.add(
            ConsentLog(
                user_id=user_id,
                auth_session_id=auth_session_id,
                document_id=document.id,
                terms_version=document.version,
                document_hash=legal_document_public_hash(document),
                language=consent.locale,
                purpose="terms_and_participation",
                client_accepted_at=accepted_at,
                ip="not_collected",
            )
        )
        await session.commit()


async def record_anonymous_consent(
    anonymous_user_hash: str,
    consent: ConsentAssertionValue,
    document: LegalDocument,
) -> None:
    """Append evidence for the purposes explicitly asserted by a visitor."""
    from backend.settings.legal import legal_document_public_hash

    public_hash = legal_document_public_hash(document)
    if not settings.COMPARIA_DB_URI:
        now = datetime.now()
        _DEV_ANONYMOUS_CONSENTS[anonymous_user_hash] = {
            "terms": {
                "version": document.version,
                "content_hash": public_hash,
                "locale": consent.locale,
                "accepted_at": now,
            },
        }
        return
    accepted_at = consent.accepted_at.replace(tzinfo=None)
    async with get_session() as session:
        session.add(
            AnonymousConsentLog(
                anonymous_user_hash=anonymous_user_hash,
                document_id=document.id,
                terms_version=document.version,
                document_hash=public_hash,
                language=consent.locale,
                purpose="terms_and_participation",
                client_accepted_at=accepted_at,
            )
        )
        await session.commit()


async def get_anonymous_consent_status(anonymous_user_hash: str) -> dict:
    if not settings.COMPARIA_DB_URI:
        return _DEV_ANONYMOUS_CONSENTS.get(
            anonymous_user_hash,
            {"terms": None},
        )
    async with get_session() as session:
        result = await session.exec(
            select(AnonymousConsentLog)
            .where(AnonymousConsentLog.anonymous_user_hash == anonymous_user_hash)
            .order_by(AnonymousConsentLog.consented_at.desc())
        )
        records = result.all()

    terms = next(
        (record for record in records if record.purpose == "terms_and_participation"),
        None,
    )
    return {
        "terms": (
            None
            if not terms
            else {
                "version": terms.terms_version,
                "content_hash": terms.document_hash,
                "locale": terms.language,
                "accepted_at": terms.consented_at,
            }
        ),
    }


async def get_current_terms_acceptance_version(
    *, user_id: uuid.UUID | None, anonymous_user_hash: str
) -> str | None:
    """Return the accepted current terms version, if any."""
    from backend.settings.legal import get_active_terms, legal_document_public_hash

    document = await get_active_terms(settings.AUTH_TERMS_LANGUAGE)
    if not document:
        return None
    public_hash = legal_document_public_hash(document)
    if not settings.COMPARIA_DB_URI:
        status = _DEV_ANONYMOUS_CONSENTS.get(anonymous_user_hash)
        terms = status.get("terms") if status else None
        accepted = bool(
            terms
            and terms["version"] == document.version
            and terms["content_hash"] == public_hash
            and terms["locale"] == document.language
        )
        return document.version if accepted else None
    async with get_session() as session:
        if user_id:
            statement = select(ConsentLog).where(
                ConsentLog.user_id == user_id,
                ConsentLog.purpose == "terms_and_participation",
                ConsentLog.document_id == document.id,
                ConsentLog.document_hash == public_hash,
            )
        else:
            statement = select(AnonymousConsentLog).where(
                AnonymousConsentLog.anonymous_user_hash == anonymous_user_hash,
                AnonymousConsentLog.purpose == "terms_and_participation",
                AnonymousConsentLog.document_id == document.id,
                AnonymousConsentLog.document_hash == public_hash,
            )
        result = await session.exec(statement)
        return document.version if result.first() is not None else None


async def has_current_terms_acceptance(
    *, user_id: uuid.UUID | None, anonymous_user_hash: str
) -> bool:
    return (
        await get_current_terms_acceptance_version(
            user_id=user_id, anonymous_user_hash=anonymous_user_hash
        )
        is not None
    )


async def erase_user_account(user_id: uuid.UUID) -> None:
    now = datetime.now()
    async with get_session() as session:
        user = await session.get(User, user_id)
        if not user or user.deleted_at is not None:
            return

        await session.execute(
            sa_update(AuthSession)
            .where(AuthSession.user_id == user_id)
            .values(revoked_at=now, ip="erased", user_agent=None)
        )
        await session.execute(
            sa_update(ConsentLog)
            .where(ConsentLog.user_id == user_id)
            .values(ip="erased")
        )
        await session.execute(
            sa_update(ConsentLog)
            .where(
                ConsentLog.user_id == user_id,
                ConsentLog.purpose == "research_data_sharing",
                ConsentLog.withdrawn_at.is_(None),
            )
            .values(withdrawn_at=now)
        )
        await session.execute(
            sa_update(Comparison)
            .where(Comparison.user_id == user_id)
            .values(user_id=None)
        )
        await session.execute(sa_delete(LoginCode).where(LoginCode.user_id == user_id))
        await session.execute(
            sa_delete(InviteToken).where(InviteToken.user_id == user_id)
        )

        user.email = f"deleted-{user.id}@deleted.invalid"
        user.deleted_at = now
        session.add(user)
        await session.commit()
