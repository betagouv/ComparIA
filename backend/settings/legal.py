import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel, Field, PlainSerializer, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from utils.database.models.auth import LegalDocument, LegalDocumentKind
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.database.settings import get_app_settings

DEFAULT_LEGAL_LANGUAGE = "fr"
LEGAL_VERSION_MAX_LENGTH = 64
LEGAL_CONTENT_MAX_LENGTH = 100_000
LEGAL_LOCALE_PATTERN = re.compile(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*")
_LOCALE_QUERY = Query(
    min_length=2, max_length=16, pattern=f"^{LEGAL_LOCALE_PATTERN.pattern}$"
)
LocaleQuery = Annotated[str, _LOCALE_QUERY]
OptionalLocaleQuery = Annotated[str | None, _LOCALE_QUERY]


def _stamp_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc)


# The columns are naive UTC. Without the marker a browser reads them as local
# time, which shifts the day a document takes effect around midnight.
UtcTimestamp = Annotated[datetime, PlainSerializer(_stamp_utc)]


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
            button_label="C’est parti",
        ),
        sign_in=SignInLegalPresentation(
            checkbox_label=(
                "J’ai pris connaissance de l’utilisation de mes données et j’accepte "
                "les conditions générales d’utilisation."
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


def normalize_effective_at(
    value: datetime | None, now: datetime | None = None
) -> datetime:
    """Return the effective date as naive UTC, like every other legal timestamp."""
    current = now or utc_now()
    effective = value or current
    if effective.tzinfo is not None:
        effective = effective.astimezone(timezone.utc).replace(tzinfo=None)
    if effective < current - timedelta(minutes=5):
        raise InvalidEffectiveDateError(
            "effective_at cannot be more than five minutes in the past"
        )
    if effective > current + timedelta(days=365):
        raise InvalidEffectiveDateError(
            "effective_at cannot be scheduled more than one year ahead"
        )
    return effective


async def list_legal_documents(
    kind: LegalDocumentKind, language: str | None = None
) -> list[LegalDocument]:
    async with get_session() as session:
        statement = select(LegalDocument).where(LegalDocument.kind == kind)
        if language:
            statement = statement.where(LegalDocument.language == language)
        result = await session.exec(
            statement.order_by(LegalDocument.effective_at.desc()).limit(100)
        )
        return list(result.all())


async def get_active_legal_document(
    kind: LegalDocumentKind, language: str
) -> LegalDocument | None:
    now = utc_now()
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


async def publish_legal_document(
    *,
    kind: LegalDocumentKind,
    version: str,
    language: str,
    content: str,
    effective_at: datetime | None,
) -> LegalDocument:
    """Publish an immutable document and retire the active one when immediate.

    Scheduled publications coexist with the current row. Active lookup orders by
    effective date, so the scheduled version takes over without creating a gap.
    """
    label = kind.replace("_", " ")
    version = version.strip()
    language = language.strip()
    if not 1 <= len(version) <= LEGAL_VERSION_MAX_LENGTH:
        raise ValueError("version must contain between 1 and 64 characters")
    if not LEGAL_LOCALE_PATTERN.fullmatch(language):
        raise ValueError("language must be a valid locale")
    if not 1 <= len(content) <= LEGAL_CONTENT_MAX_LENGTH:
        raise ValueError("content must contain between 1 and 100000 characters")

    now = utc_now()
    normalized_effective_at = normalize_effective_at(effective_at, now)
    digest = legal_document_hash(content)

    async with get_session() as session:
        existing_result = await session.exec(
            select(LegalDocument).where(
                LegalDocument.kind == kind,
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
                    f"this {label} version is already published with different "
                    "content or date"
                )
            return existing

        document = LegalDocument(
            kind=kind,
            version=version,
            language=language,
            content=content,
            content_hash=digest,
            effective_at=normalized_effective_at,
        )
        if normalized_effective_at <= now:
            active_result = await session.exec(
                select(LegalDocument)
                .where(
                    LegalDocument.kind == kind,
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
                f"this {label} version was published concurrently"
            ) from exc
        await session.refresh(document)
        return document
