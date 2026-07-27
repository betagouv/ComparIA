import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr, Field

from backend.admin.llms import admin_llms_router
from backend.admin.services import (
    CannotDeleteLastAdminError,
    CannotDeleteSelfError,
    CannotDemoteLastAdminError,
    EmailAlreadyExistsError,
    cancel_user_invite,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)
from backend.admin.suggestions import router as admin_suggestions_router
from backend.auth.dependencies import RequiredAdmin, require_admin
from backend.auth.email import send_invite_link
from backend.auth.services import create_invite
from backend.config import settings
from backend.settings.legal import (
    DEFAULT_LEGAL_LANGUAGE,
    LEGAL_CONTENT_MAX_LENGTH,
    LEGAL_LOCALE_PATTERN,
    LEGAL_VERSION_MAX_LENGTH,
    DuplicateLegalDocumentError,
    InvalidEffectiveDateError,
    LegalPresentation,
    LocaleQuery,
    OptionalLocaleQuery,
    UtcTimestamp,
    get_active_legal_document,
    get_legal_presentation,
    list_legal_documents,
    publish_legal_document,
)
from utils.database.models.app_settings import (
    AppSettings,
    AppSettingsPatch,
    AppSettingsPublic,
)
from utils.database.models.auth import (
    LegalDocument,
    LegalDocumentKind,
    UserPublic,
    UserUpsert,
)
from utils.database.settings import get_app_settings, update_app_settings
from utils.utils import FormJsonSchema

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

router.include_router(admin_llms_router)
router.include_router(admin_suggestions_router)


class UsersPage(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int


class InviteBody(BaseModel):
    email: EmailStr


class AdminLegalDocument(BaseModel):
    id: uuid.UUID
    kind: LegalDocumentKind
    version: str
    locale: str
    content: str
    content_hash: str
    published_at: UtcTimestamp
    effective_at: UtcTimestamp
    retired_at: UtcTimestamp | None


class PublishLegalDocumentBody(BaseModel):
    version: str = Field(
        min_length=1, max_length=LEGAL_VERSION_MAX_LENGTH, pattern=r"^\S(?:.*\S)?$"
    )
    locale: str = Field(
        min_length=2,
        max_length=16,
        pattern=f"^{LEGAL_LOCALE_PATTERN.pattern}$",
    )
    content: str = Field(min_length=1, max_length=LEGAL_CONTENT_MAX_LENGTH)
    effective_at: datetime | None = None
    confirm_publication: Literal[True]


class UpdateLegalPresentationBody(BaseModel):
    presentation: LegalPresentation


_LOGO_MAX_SIZE = 2 * 1024 * 1024
_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}


def _to_admin_legal_document(row: LegalDocument) -> AdminLegalDocument:
    return AdminLegalDocument(
        id=row.id,
        kind=row.kind,
        version=row.version,
        locale=row.language,
        content=row.content,
        content_hash=row.content_hash,
        published_at=row.published_at,
        effective_at=row.effective_at,
        retired_at=row.retired_at,
    )


async def _current_legal_document(
    kind: LegalDocumentKind, locale: str
) -> AdminLegalDocument:
    document = await get_active_legal_document(kind, locale)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active document is available for this locale",
        )
    return _to_admin_legal_document(document)


async def _publish(
    kind: LegalDocumentKind, body: PublishLegalDocumentBody
) -> AdminLegalDocument:
    try:
        document = await publish_legal_document(
            kind=kind,
            version=body.version,
            language=body.locale,
            content=body.content,
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


@router.get("/legal/terms", response_model=list[AdminLegalDocument])
async def get_terms_publications(
    locale: OptionalLocaleQuery = None,
) -> list[AdminLegalDocument]:
    documents = await list_legal_documents("terms", locale)
    return [_to_admin_legal_document(document) for document in documents]


@router.get("/legal/terms/current", response_model=AdminLegalDocument)
async def get_current_terms(
    locale: LocaleQuery = DEFAULT_LEGAL_LANGUAGE,
) -> AdminLegalDocument:
    return await _current_legal_document("terms", locale)


@router.post(
    "/legal/terms",
    response_model=AdminLegalDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_terms_publication(
    body: PublishLegalDocumentBody,
) -> AdminLegalDocument:
    return await _publish("terms", body)


@router.get("/legal/privacy-policy", response_model=list[AdminLegalDocument])
async def get_privacy_policy_publications(
    locale: OptionalLocaleQuery = None,
) -> list[AdminLegalDocument]:
    documents = await list_legal_documents("privacy_policy", locale)
    return [_to_admin_legal_document(document) for document in documents]


@router.get("/legal/privacy-policy/current", response_model=AdminLegalDocument)
async def get_current_privacy_policy(
    locale: LocaleQuery = DEFAULT_LEGAL_LANGUAGE,
) -> AdminLegalDocument:
    return await _current_legal_document("privacy_policy", locale)


@router.post(
    "/legal/privacy-policy",
    response_model=AdminLegalDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_privacy_policy_publication(
    body: PublishLegalDocumentBody,
) -> AdminLegalDocument:
    return await _publish("privacy_policy", body)


@router.get("/legal/presentation", response_model=LegalPresentation)
async def get_participation_presentation() -> LegalPresentation:
    return await get_legal_presentation()


@router.put("/legal/presentation", response_model=LegalPresentation)
async def put_participation_presentation(
    body: UpdateLegalPresentationBody,
    current_user: RequiredAdmin,
) -> LegalPresentation:
    await update_app_settings(
        {"legal_presentation": body.presentation.model_dump(mode="json")},
        updated_by=current_user.id,
    )
    return body.presentation


@router.get("/users", response_model=UsersPage)
async def get_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> UsersPage:
    rows, total = await list_users(search=search, page=page, page_size=page_size)
    return UsersPage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/users/schema")
async def get_user_schema():
    return UserUpsert.model_json_schema(schema_generator=FormJsonSchema)


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user_route(body: UserUpsert) -> UserPublic:
    try:
        return await create_user(body)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user_route(user_id: uuid.UUID) -> UserPublic:
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user


@router.put("/users/{user_id}", response_model=UserPublic)
async def update_user_route(user_id: uuid.UUID, body: UserUpsert) -> UserPublic:
    try:
        user = await update_user(user_id, body)
    except CannotDemoteLastAdminError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the last remaining admin",
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: uuid.UUID,
    current_user: RequiredAdmin,
) -> None:
    try:
        deleted = await delete_user(user_id, current_user.id)
    except CannotDeleteSelfError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    except CannotDeleteLastAdminError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last remaining admin",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/users/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_user(
    body: InviteBody,
    current_user: RequiredAdmin,
) -> None:
    token = await create_invite(body.email, invited_by=current_user.id)
    link = f"{settings.COMPARIA_APP_URL}/invite/{token}"
    await send_invite_link(body.email, link)


@router.delete("/users/{user_id}/invite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_invite(user_id: uuid.UUID) -> None:
    canceled = await cancel_user_invite(user_id)
    if not canceled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _to_app_settings_public(row: AppSettings) -> AppSettingsPublic:
    return AppSettingsPublic(
        auth_access_policy=row.auth_access_policy,
        auth_domain_allowlist=row.auth_domain_allowlist,
        votes_objective=row.votes_objective,
        platform_name=row.platform_name,
        has_custom_logo=row.logo is not None,
        updated_at=row.updated_at.isoformat(),
        updated_by=row.updated_by,
    )


@router.get("/settings", response_model=AppSettingsPublic)
async def get_settings() -> AppSettingsPublic:
    row = await get_app_settings()
    return _to_app_settings_public(row)


@router.patch("/settings", response_model=AppSettingsPublic)
async def patch_settings(
    body: AppSettingsPatch,
    current_user: RequiredAdmin,
) -> AppSettingsPublic:
    row = await update_app_settings(
        body.model_dump(exclude_unset=True), updated_by=current_user.id
    )
    return _to_app_settings_public(row)


@router.put("/settings/logo", response_model=AppSettingsPublic)
async def upload_logo(
    current_user: RequiredAdmin,
    file: UploadFile,
) -> AppSettingsPublic:
    if file.content_type not in _LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}",
        )
    content = await file.read()
    if len(content) > _LOGO_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file is too large (max 2 MB)",
        )
    row = await update_app_settings(
        {"logo": content, "logo_content_type": file.content_type},
        updated_by=current_user.id,
    )
    return _to_app_settings_public(row)


@router.delete("/settings/logo", response_model=AppSettingsPublic)
async def remove_logo(current_user: RequiredAdmin) -> AppSettingsPublic:
    row = await update_app_settings(
        {"logo": None, "logo_content_type": None}, updated_by=current_user.id
    )
    return _to_app_settings_public(row)
