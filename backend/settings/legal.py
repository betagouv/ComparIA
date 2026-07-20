import hashlib
import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlsplit

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
LEGAL_INTERNAL_LINKS = {
    "/accessibilite",
    "/arene/donnees-personnelles",
    "/arene/modalites",
    "/donnees-personnelles",
    "/modalites",
    "/terms",
}
LEGAL_EXTERNAL_LINK_HOSTS = {
    "beta.gouv.fr",
    "cnil.fr",
    "comparia.beta.gouv.fr",
    "www.cnil.fr",
}


class LegalPresentationLink(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    href: str = Field(min_length=1, max_length=2_048)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("link label cannot be blank")
        return value

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: str) -> str:
        value = value.strip()
        parsed = urlsplit(value)
        if value.startswith("/") and not value.startswith("//"):
            if parsed.scheme or parsed.netloc or parsed.query:
                raise ValueError(
                    "internal legal links cannot contain an origin or query"
                )
            if parsed.path not in LEGAL_INTERNAL_LINKS:
                raise ValueError("internal legal link is not an allowed legal route")
            return value
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.hostname.lower() not in LEGAL_EXTERNAL_LINK_HOSTS
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
            or parsed.query
        ):
            raise ValueError("external legal link must use an allowlisted HTTPS host")
        return value


class ArenaLegalPresentation(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    introduction: str = Field(min_length=1, max_length=2_000)
    checkbox_label: str = Field(min_length=1, max_length=2_000)
    links: list[LegalPresentationLink] = Field(min_length=1, max_length=5)
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
    links: list[LegalPresentationLink] = Field(min_length=1, max_length=5)

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


class LegalDocumentEnvelope(BaseModel):
    schema_version: Literal[1] = 1
    content: str = Field(min_length=1, max_length=LEGAL_CONTENT_MAX_LENGTH)
    presentation: LegalPresentation

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("legal document content cannot be blank")
        return value


def fallback_legal_presentation() -> LegalPresentation:
    """Current UI copy, retained only to decode pre-envelope publications."""
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
            links=[
                LegalPresentationLink(
                    label="Conditions générales d’utilisation",
                    href="/arene/modalites",
                ),
                LegalPresentationLink(
                    label="Politique de confidentialité",
                    href="/arene/donnees-personnelles",
                ),
            ],
            button_label="C'est parti",
        ),
        sign_in=SignInLegalPresentation(
            checkbox_label=(
                "J'ai pris connaissance de l'utilisation de mes données et j'accepte "
                "les conditions générales d'utilisation."
            ),
            links=[
                LegalPresentationLink(
                    label="Conditions générales d’utilisation",
                    href="/arene/modalites",
                ),
                LegalPresentationLink(
                    label="Politique de confidentialité",
                    href="/arene/donnees-personnelles",
                ),
            ],
        ),
    )


async def get_legal_presentation(
    terms_document: LegalDocument | None = None,
) -> LegalPresentation:
    """Return the mutable journey copy, falling back to the active terms snapshot."""
    app_settings = await get_app_settings()
    if app_settings.legal_presentation:
        return LegalPresentation.model_validate(app_settings.legal_presentation)

    document = terms_document or await get_active_terms(settings.AUTH_TERMS_LANGUAGE)
    if document:
        return decode_legal_document(document.content).presentation
    return fallback_legal_presentation()


def legal_document_envelope(
    content: str, presentation: LegalPresentation
) -> LegalDocumentEnvelope:
    return LegalDocumentEnvelope(content=content, presentation=presentation)


def serialize_legal_document(envelope: LegalDocumentEnvelope) -> str:
    return json.dumps(
        envelope.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def decode_legal_document(raw_content: str) -> LegalDocumentEnvelope:
    try:
        value = json.loads(raw_content)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, dict) and value.get("schema_version") == 1:
        return LegalDocumentEnvelope.model_validate(value)
    return legal_document_envelope(raw_content, fallback_legal_presentation())


class DuplicateLegalDocumentError(ValueError):
    """Raised when a published version is reused with different attributes."""


class InvalidEffectiveDateError(ValueError):
    """Raised when a publication date is outside the supported window."""


def legal_document_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def legal_envelope_hash(envelope: LegalDocumentEnvelope) -> str:
    return legal_document_hash(serialize_legal_document(envelope))


def legal_document_public_hash(document: LegalDocument) -> str:
    return legal_envelope_hash(decode_legal_document(document.content))


def normalize_effective_at(
    value: datetime | None, now: datetime | None = None
) -> datetime:
    """Return a naive UTC timestamp accepted by the database model."""
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
    presentation: LegalPresentation,
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
    envelope = legal_document_envelope(content, presentation)
    serialized_content = serialize_legal_document(envelope)
    digest = legal_envelope_hash(envelope)

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
            existing_envelope = decode_legal_document(existing.content)
            if (
                legal_document_public_hash(existing) != digest
                or existing_envelope != envelope
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
            content=serialized_content,
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
            content=serialize_legal_document(
                legal_document_envelope(
                    settings.AUTH_TERMS_CONTENT, fallback_legal_presentation()
                )
            ),
            content_hash=legal_envelope_hash(
                legal_document_envelope(
                    settings.AUTH_TERMS_CONTENT, fallback_legal_presentation()
                )
            ),
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
    """Publish an immutable privacy policy independently from accepted terms."""
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


async def ensure_bootstrap_terms() -> LegalDocument:
    """Create the configured initial terms once for fresh installations.

    Published rows are never updated. Operators must change the configured
    version when changing content; a mismatched digest is rejected to prevent
    silently rewriting a document that users already accepted.
    """
    if not (1 <= len(settings.AUTH_TERMS_VERSION) <= 64):
        raise RuntimeError(
            "AUTH_TERMS_VERSION must contain between 1 and 64 characters"
        )
    if not re.fullmatch(
        r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", settings.AUTH_TERMS_LANGUAGE
    ):
        raise RuntimeError("AUTH_TERMS_LANGUAGE must be a valid locale")
    if not (1 <= len(settings.AUTH_TERMS_CONTENT) <= 100_000):
        raise RuntimeError(
            "AUTH_TERMS_CONTENT must contain between 1 and 100000 characters"
        )
    envelope = legal_document_envelope(
        settings.AUTH_TERMS_CONTENT, fallback_legal_presentation()
    )
    serialized_content = serialize_legal_document(envelope)
    digest = legal_envelope_hash(envelope)
    async with get_session() as session:
        result = await session.exec(
            select(LegalDocument).where(
                LegalDocument.kind == "terms",
                LegalDocument.version == settings.AUTH_TERMS_VERSION,
                LegalDocument.language == settings.AUTH_TERMS_LANGUAGE,
            )
        )
        document = result.first()
        if document:
            is_legacy_match = (
                document.content == settings.AUTH_TERMS_CONTENT
                and document.content_hash
                == legal_document_hash(settings.AUTH_TERMS_CONTENT)
            )
            if legal_document_public_hash(document) != digest and not is_legacy_match:
                raise RuntimeError(
                    "AUTH_TERMS_CONTENT changed without a new AUTH_TERMS_VERSION"
                )
            return document

        document = LegalDocument(
            kind="terms",
            version=settings.AUTH_TERMS_VERSION,
            language=settings.AUTH_TERMS_LANGUAGE,
            content=serialized_content,
            content_hash=digest,
            effective_at=datetime.now(),
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


async def validate_active_terms(
    version: str, content_hash: str, language: str
) -> LegalDocument | None:
    document = await get_active_terms(language)
    if not document:
        return None
    if (
        document.version != version
        or legal_document_public_hash(document) != content_hash
    ):
        return None
    return document
