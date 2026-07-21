from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from backend.config import settings
from backend.settings.legal import (
    LegalPresentation,
    get_active_privacy_policy,
    get_active_terms,
    get_legal_presentation,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class PublicLegalDocument(BaseModel):
    version: str
    content_hash: str
    locale: str
    content: str
    published_at: datetime
    effective_at: datetime
    presentation: LegalPresentation


class PublicPrivacyPolicyDocument(BaseModel):
    version: str
    content_hash: str
    locale: str
    content: str
    published_at: datetime
    effective_at: datetime


@router.get("/legal/terms")
async def public_terms(
    locale: str = Query(
        default="fr",
        min_length=2,
        max_length=16,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    ),
) -> PublicLegalDocument:
    document = await get_active_terms(locale)
    if not document and locale != settings.AUTH_TERMS_LANGUAGE:
        document = await get_active_terms(settings.AUTH_TERMS_LANGUAGE)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published terms are available for this locale.",
        )
    return PublicLegalDocument(
        version=document.version,
        content_hash=document.content_hash,
        locale=document.language,
        content=document.content,
        published_at=document.published_at,
        effective_at=document.effective_at,
        presentation=await get_legal_presentation(),
    )


@router.get("/legal/privacy-policy")
async def public_privacy_policy(
    locale: str = Query(
        default="fr",
        min_length=2,
        max_length=16,
        pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
    ),
) -> PublicPrivacyPolicyDocument:
    document = await get_active_privacy_policy(locale)
    if not document and locale != settings.AUTH_TERMS_LANGUAGE:
        document = await get_active_privacy_policy(settings.AUTH_TERMS_LANGUAGE)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No published privacy policy is available for this locale.",
        )
    return PublicPrivacyPolicyDocument(
        version=document.version,
        content_hash=document.content_hash,
        locale=document.language,
        content=document.content,
        published_at=document.published_at,
        effective_at=document.effective_at,
    )
