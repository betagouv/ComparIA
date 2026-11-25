import logging
import uuid
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth.dependencies import RequiredAdmin
from backend.settings.informational_legal import (
    InformationalLegalPage,
    InformationalLegalPages,
    LegalPageKey,
    get_informational_legal_page,
    get_informational_legal_pages,
)
from backend.settings.legal import (
    LEGAL_CONTENT_MAX_LENGTH,
    LEGAL_VERSION_MAX_LENGTH,
    CookieBannerTranslatable,
    DuplicateLegalDocumentError,
    InvalidEffectiveDateError,
    LegalPresentationTranslatable,
    UtcTimestamp,
    get_active_legal_document,
    get_legal_presentations,
    get_written_cookie_banners,
    list_legal_documents,
    publish_legal_document,
)
from utils.database.models.auth import (
    LegalDocument,
    LegalDocumentKind,
)
from utils.database.settings import get_app_settings, update_app_settings
from utils.i18n import TranslatableRaw
from utils.validation import Translatable

logger = logging.getLogger("languia")

router = APIRouter(prefix="/legal", tags=["legal"])


class AdminLegalDocument(BaseModel):
    id: uuid.UUID
    kind: LegalDocumentKind
    version: str
    content: TranslatableRaw[str]
    content_hash: str
    published_at: UtcTimestamp
    effective_at: UtcTimestamp
    retired_at: UtcTimestamp | None


class PublishLegalDocumentBody(BaseModel):
    version: str = Field(
        min_length=1, max_length=LEGAL_VERSION_MAX_LENGTH, pattern=r"^\S(?:.*\S)?$"
    )
    content: Translatable[
        Annotated[str, Field(min_length=1, max_length=LEGAL_CONTENT_MAX_LENGTH)]
    ]
    effective_at: datetime | None = None
    confirm_publication: Literal[True]


class LegalStatuses(BaseModel, extra="forbid"):
    class LegalStatus(BaseModel, extra="forbid"):
        published: bool
        missing_locales: bool

    participation: LegalStatus
    cookies: LegalStatus
    terms: LegalStatus
    privacy_policy: LegalStatus
    legal_notice: LegalStatus
    accessibility: LegalStatus
    ecodesign: LegalStatus


@router.get("/status", response_model=LegalStatuses)
async def get_admin_legal_pages_status() -> LegalStatuses:
    settings = await get_app_settings()
    enabled_locales = set(settings.enabled_locales)
    status = {}

    participation_locales = set((await get_legal_presentations()).root)
    status["participation"] = {
        "published": settings.default_locale in participation_locales,
        "missing_locales": enabled_locales != participation_locales,
    }

    cookie_banner_locales = set((await get_written_cookie_banners()).root)
    status["cookies"] = {
        "published": settings.cookie_banner_enabled,
        "missing_locales": not enabled_locales <= cookie_banner_locales,
    }

    for k, page in await get_informational_legal_pages():
        if page.mode == "internal":
            locales = set(page.content_by_locale.root)
            status[k] = {
                "published": settings.default_locale in locales,
                "missing_locales": enabled_locales != locales,
            }
        else:
            status[k] = {"published": True, "missing_locales": False}

    for k in ("terms", "privacy_policy"):
        doc = await get_active_legal_document(k)
        locales = set(doc.content) if doc else set()
        status[k] = {
            "published": settings.default_locale in locales,
            "missing_locales": enabled_locales != locales,
        }

    return status


@router.get("/informational-page/{key}", response_model=InformationalLegalPage)
async def get_admin_informational_legal_page(
    key: LegalPageKey,
) -> InformationalLegalPage:
    return await get_informational_legal_page(key)


@router.put("/informational-page/{key}", response_model=InformationalLegalPage)
async def put_admin_informational_legal_page(
    key: LegalPageKey,
    body: InformationalLegalPage,
    current_user: RequiredAdmin,
) -> InformationalLegalPages:
    pages = await get_informational_legal_pages()
    setattr(pages, key, body)
    await update_app_settings(
        {"informational_legal_pages": pages.model_dump(mode="json")},
        updated_by=current_user.id,
    )
    return body


def _to_admin_legal_document(row: LegalDocument) -> AdminLegalDocument:
    return AdminLegalDocument(
        id=row.id,
        kind=row.kind,
        version=row.version,
        content=row.content,
        content_hash=row.content_hash,
        published_at=row.published_at,
        effective_at=row.effective_at,
        retired_at=row.retired_at,
    )


async def _current_legal_document(kind: LegalDocumentKind) -> AdminLegalDocument:
    document = await get_active_legal_document(kind)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active '{kind}' document found",
        )
    return _to_admin_legal_document(document)


async def _publish(
    kind: LegalDocumentKind, body: PublishLegalDocumentBody
) -> AdminLegalDocument:
    try:
        document = await publish_legal_document(
            kind=kind,
            version=body.version,
            content=body.content.root,
            effective_at=body.effective_at,
        )
    except DuplicateLegalDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (InvalidEffectiveDateError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _to_admin_legal_document(document)


@router.get("/documents/{key}", response_model=list[AdminLegalDocument])
async def get_legal_doc_publications(
    key: LegalDocumentKind,
) -> list[AdminLegalDocument]:
    documents = await list_legal_documents(key)
    return [_to_admin_legal_document(document) for document in documents]


@router.get("/documents/{key}/current", response_model=AdminLegalDocument)
async def get_legal_doc_current(key: LegalDocumentKind) -> AdminLegalDocument:
    return await _current_legal_document(key)


@router.post(
    "/documents/{key}",
    response_model=AdminLegalDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_legal_doc_publication(
    key: LegalDocumentKind,
    body: PublishLegalDocumentBody,
) -> AdminLegalDocument:
    return await _publish(key, body)


@router.get("/presentation", response_model=LegalPresentationTranslatable)
async def get_participation_presentations() -> LegalPresentationTranslatable:
    return await get_legal_presentations()


@router.put("/presentation", response_model=LegalPresentationTranslatable)
async def put_participation_presentation(
    body: LegalPresentationTranslatable,
    current_user: RequiredAdmin,
) -> LegalPresentationTranslatable:
    await update_app_settings(
        {"legal_presentation": body.model_dump(mode="json")},
        updated_by=current_user.id,
    )
    return body


@router.get("/cookies", response_model=CookieBannerTranslatable)
async def get_cookie_banner() -> CookieBannerTranslatable:
    # What the admin wrote, not the public text: the form saves it back whole.
    return await get_written_cookie_banners()


@router.put("/cookies", response_model=CookieBannerTranslatable)
async def put_cookie_banner(
    body: CookieBannerTranslatable,
    current_user: RequiredAdmin,
) -> CookieBannerTranslatable:
    await update_app_settings(
        {"cookie_banner": body.model_dump(mode="json")},
        updated_by=current_user.id,
    )
    return body
