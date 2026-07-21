import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from backend.config import settings
from utils.database.models.auth import LegalDocument
from utils.database.session import get_session
from utils.database.settings import get_app_settings

LEGAL_VERSION_MAX_LENGTH = 64
LEGAL_CONTENT_MAX_LENGTH = 100_000
LEGAL_LOCALE_PATTERN = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")


class ArenaLegalPresentation(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    introduction: str = Field(min_length=1, max_length=2_000)
    checkbox_label: str = Field(min_length=1, max_length=2_000)
    button_label: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator("title", "introduction", "checkbox_label", "button_label")
    @classmethod
    def normalize_copy(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("presentation copy cannot be blank")
        return value


class SignInLegalPresentation(BaseModel):
    checkbox_label: str = Field(min_length=1, max_length=2_000)

    @field_validator("checkbox_label")
    @classmethod
    def normalize_copy(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("presentation copy cannot be blank")
        return value


class LegalPresentation(BaseModel):
    arena: ArenaLegalPresentation
    sign_in: SignInLegalPresentation


def fallback_legal_presentation() -> LegalPresentation:
    return LegalPresentation(
        arena=ArenaLegalPresentation(
            title="Avant de commencer",
            introduction=(
                "Vos messages sont transmis aux modèles d’IA comparés. Ne saisissez "
                "aucune donnée sensible ou permettant d’identifier une personne."
            ),
            checkbox_label=(
                "J’ai lu et j’accepte les conditions générales d’utilisation. Je "
                "comprends que participer implique le traitement de mes messages par "
                "des modèles d’IA et la réutilisation des conversations et votes pour "
                "l’évaluation, la recherche et la production de jeux de données."
            ),
            button_label="C'est parti",
        ),
        sign_in=SignInLegalPresentation(
            checkbox_label=(
                "J'ai pris connaissance de l'utilisation de mes données et j'accepte "
                "les conditions générales d'utilisation."
            ),
        ),
    )


async def get_legal_presentation() -> LegalPresentation:
    app_settings = await get_app_settings()
    if app_settings.legal_presentation:
        return LegalPresentation.model_validate(app_settings.legal_presentation)
    return fallback_legal_presentation()


class DuplicateLegalDocumentError(ValueError):
    pass


class InvalidEffectiveDateError(ValueError):
    pass


def legal_document_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def legal_document_public_hash(document: LegalDocument) -> str:
    return document.content_hash


def normalize_effective_at(
    value: datetime | None, now: datetime | None = None
) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    effective = value or current
    if effective.tzinfo is None:
        effective = effective.replace(tzinfo=timezone.utc)
    else:
        effective = effective.astimezone(timezone.utc)
    if effective < current - timedelta(minutes=5):
        raise InvalidEffectiveDateError(
            "effective_at cannot be more than five minutes in the past"
        )
    if effective > current + timedelta(days=365):
        raise InvalidEffectiveDateError(
            "effective_at cannot be scheduled more than one year ahead"
        )
    return effective.replace(tzinfo=None)


async def list_terms(language: str | None = None) -> list[LegalDocument]:
    return await list_legal_documents("terms", language)


async def list_privacy_policies(language: str | None = None) -> list[LegalDocument]:
    return await list_legal_documents("privacy_policy", language)


async def list_legal_documents(
    kind: Literal["terms", "privacy_policy"], language: str | None = None
) -> list[LegalDocument]:
    if not settings.COMPARIA_DB_URI:
        document = await get_active_legal_document(
            kind, language or settings.AUTH_TERMS_LANGUAGE
        )
        return [document] if document else []
    async with get_session() as session:
        statement = select(LegalDocument).where(LegalDocument.kind == kind)
        if language:
            statement = statement.where(LegalDocument.language == language)
        result = await session.exec(
            statement.order_by(LegalDocument.effective_at.desc()).limit(100)
        )
        return list(result.all())


async def publish_terms(
    *,
    version: str,
    language: str,
    content: str,
    effective_at: datetime | None,
) -> LegalDocument:
    """Publish immutable terms and retire the currently active row when immediate.

    Scheduled publications coexist with the current row. Active lookup orders by
    effective date, so the scheduled version takes over without creating a gap.
    """
    version = version.strip()
    language = language.strip()
    if not 1 <= len(version) <= LEGAL_VERSION_MAX_LENGTH:
        raise ValueError("version must contain between 1 and 64 characters")
    if not LEGAL_LOCALE_PATTERN.fullmatch(language):
        raise ValueError("language must be a valid locale")
    if not 1 <= len(content) <= LEGAL_CONTENT_MAX_LENGTH:
        raise ValueError("content must contain between 1 and 100000 characters")

    now = datetime.now(timezone.utc)
    normalized_effective_at = normalize_effective_at(effective_at, now)
    now_naive = now.replace(tzinfo=None)
    digest = legal_document_hash(content)

    async with get_session() as session:
        existing_result = await session.exec(
            select(LegalDocument).where(
                LegalDocument.kind == "terms",
                LegalDocument.version == version,
                LegalDocument.language == language,
            )
        )
        existing = existing_result.first()
        if existing:
            if (
                existing.content_hash != digest
                or existing.content != content
                or existing.effective_at != normalized_effective_at
            ):
                raise DuplicateLegalDocumentError(
                    "this terms version is already published with different content or date"
                )
            return existing

        document = LegalDocument(
            kind="terms",
            version=version,
            language=language,
            content=content,
            content_hash=digest,
            effective_at=normalized_effective_at,
        )
        if normalized_effective_at <= now_naive:
            active_result = await session.exec(
                select(LegalDocument)
                .where(
                    LegalDocument.kind == "terms",
                    LegalDocument.language == language,
                    LegalDocument.effective_at <= normalized_effective_at,
                    LegalDocument.retired_at.is_(None),
                )
                .with_for_update()
            )
            for active_document in active_result.all():
                active_document.retired_at = normalized_effective_at
                session.add(active_document)
        session.add(document)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise DuplicateLegalDocumentError(
                "this terms version was published concurrently"
            ) from exc
        await session.refresh(document)
        return document


async def get_active_terms(language: str) -> LegalDocument | None:
    return await get_active_legal_document("terms", language)


async def get_active_privacy_policy(language: str) -> LegalDocument | None:
    return await get_active_legal_document("privacy_policy", language)


async def get_active_legal_document(
    kind: Literal["terms", "privacy_policy"], language: str
) -> LegalDocument | None:
    if not settings.COMPARIA_DB_URI:
        if kind == "privacy_policy":
            return None
        if language != settings.AUTH_TERMS_LANGUAGE:
            return None
        return LegalDocument(
            id=uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"comparia:terms:{settings.AUTH_TERMS_LANGUAGE}:{settings.AUTH_TERMS_VERSION}",
            ),
            kind="terms",
            version=settings.AUTH_TERMS_VERSION,
            language=settings.AUTH_TERMS_LANGUAGE,
            content=settings.AUTH_TERMS_CONTENT,
            content_hash=legal_document_hash(settings.AUTH_TERMS_CONTENT),
            published_at=datetime(2026, 1, 1),
            effective_at=datetime(2026, 1, 1),
        )
    now = datetime.now()
    async with get_session() as session:
        result = await session.exec(
            select(LegalDocument)
            .where(
                LegalDocument.kind == kind,
                LegalDocument.language == language,
                LegalDocument.effective_at <= now,
                LegalDocument.retired_at.is_(None),
            )
            .order_by(LegalDocument.effective_at.desc())
        )
        return result.first()


async def publish_privacy_policy(
    *,
    version: str,
    language: str,
    content: str,
    effective_at: datetime | None,
) -> LegalDocument:
    version = version.strip()
    language = language.strip()
    if not 1 <= len(version) <= LEGAL_VERSION_MAX_LENGTH:
        raise ValueError("version must contain between 1 and 64 characters")
    if not LEGAL_LOCALE_PATTERN.fullmatch(language):
        raise ValueError("language must be a valid locale")
    if not 1 <= len(content) <= LEGAL_CONTENT_MAX_LENGTH:
        raise ValueError("content must contain between 1 and 100000 characters")

    now = datetime.now(timezone.utc)
    normalized_effective_at = normalize_effective_at(effective_at, now)
    now_naive = now.replace(tzinfo=None)
    digest = legal_document_hash(content)

    async with get_session() as session:
        existing_result = await session.exec(
            select(LegalDocument).where(
                LegalDocument.kind == "privacy_policy",
                LegalDocument.version == version,
                LegalDocument.language == language,
            )
        )
        existing = existing_result.first()
        if existing:
            if (
                existing.content_hash != digest
                or existing.content != content
                or existing.effective_at != normalized_effective_at
            ):
                raise DuplicateLegalDocumentError(
                    "this privacy policy version is already published with different content or date"
                )
            return existing

        document = LegalDocument(
            kind="privacy_policy",
            version=version,
            language=language,
            content=content,
            content_hash=digest,
            effective_at=normalized_effective_at,
        )
        if normalized_effective_at <= now_naive:
            active_result = await session.exec(
                select(LegalDocument)
                .where(
                    LegalDocument.kind == "privacy_policy",
                    LegalDocument.language == language,
                    LegalDocument.effective_at <= normalized_effective_at,
                    LegalDocument.retired_at.is_(None),
                )
                .with_for_update()
            )
            for active_document in active_result.all():
                active_document.retired_at = normalized_effective_at
                session.add(active_document)
        session.add(document)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise DuplicateLegalDocumentError(
                "this privacy policy version was published concurrently"
            ) from exc
        await session.refresh(document)
        return document


async def validate_active_terms(
    version: str, content_hash: str, language: str
) -> LegalDocument | None:
    document = await get_active_terms(language)
    if not document:
        return None
    if document.version != version or document.content_hash != content_hash:
        return None
    return document
