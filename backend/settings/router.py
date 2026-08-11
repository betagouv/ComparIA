import hashlib

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel

from backend.settings.legal import (
    DEFAULT_LEGAL_LANGUAGE,
    LegalPresentation,
    LocaleQuery,
    UtcTimestamp,
    get_active_legal_document,
    get_legal_presentation,
)
from backend.settings.informational_legal import (
    InformationalLegalPages,
    get_informational_legal_pages,
)
from utils.database.models.auth import LegalDocument, LegalDocumentKind

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/legal/informational-pages", response_model=InformationalLegalPages)
async def public_informational_legal_pages() -> InformationalLegalPages:
    return await get_informational_legal_pages()


class PublicLegalDocument(BaseModel):
    version: str
    content_hash: str
    locale: str
    content: str
    published_at: UtcTimestamp
    effective_at: UtcTimestamp


class PublicTermsDocument(PublicLegalDocument):
    presentation: LegalPresentation


async def _active_document(kind: LegalDocumentKind, locale: str) -> LegalDocument:
    document = await get_active_legal_document(kind, locale)
    if not document and locale != DEFAULT_LEGAL_LANGUAGE:
        document = await get_active_legal_document(kind, DEFAULT_LEGAL_LANGUAGE)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published document is available for this locale.",
        )
    return document


def _cache_headers(*parts: str) -> dict[str, str]:
    """Strong ETag over the whole payload.

    A published document never changes, but the active one does when a new
    version takes effect, so clients must revalidate rather than cache blindly.
    """
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
    return {"ETag": f'"{digest}"', "Cache-Control": "no-cache"}


@router.get("/legal/terms", response_model=PublicTermsDocument)
async def public_terms(
    request: Request, response: Response, locale: LocaleQuery = DEFAULT_LEGAL_LANGUAGE
):
    document = await _active_document("terms", locale)
    presentation = await get_legal_presentation()
    # The presentation is part of the payload, so editing it must invalidate
    # the cached response even though the document itself is unchanged.
    headers = _cache_headers(document.content_hash, presentation.model_dump_json())
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    response.headers.update(headers)
    return PublicTermsDocument(
        version=document.version,
        content_hash=document.content_hash,
        locale=document.language,
        content=document.content,
        published_at=document.published_at,
        effective_at=document.effective_at,
        presentation=presentation,
    )


@router.get("/legal/privacy-policy", response_model=PublicLegalDocument)
async def public_privacy_policy(
    request: Request, response: Response, locale: LocaleQuery = DEFAULT_LEGAL_LANGUAGE
):
    document = await _active_document("privacy_policy", locale)
    headers = _cache_headers(document.content_hash)
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    response.headers.update(headers)
    return PublicLegalDocument(
        version=document.version,
        content_hash=document.content_hash,
        locale=document.language,
        content=document.content,
        published_at=document.published_at,
        effective_at=document.effective_at,
    )
