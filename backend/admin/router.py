import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr

from backend.admin.llms import admin_llms_router
from backend.admin.services import (
    CannotDeleteLastAdminError,
    CannotDeleteSelfError,
    cancel_user_invite,
    delete_user,
    list_users,
    set_user_role,
)
from backend.auth.dependencies import RequiredAdmin, require_admin
from backend.auth.email import send_invite_link
from backend.auth.services import create_invite
from backend.config import settings
from utils.database.models.app_settings import AppSettingsPatch, AppSettingsPublic
from utils.database.models.auth import UserPublic, UserRole
from utils.database.settings import to_app_settings_public, update_app_settings

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

router.include_router(admin_llms_router)


class UsersPage(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int


class SetRoleBody(BaseModel):
    role: UserRole


class InviteBody(BaseModel):
    email: EmailStr


_LOGO_MAX_SIZE = 2 * 1024 * 1024
_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}


@router.get("/users", response_model=UsersPage)
async def get_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> UsersPage:
    rows, total = await list_users(search=search, page=page, page_size=page_size)
    return UsersPage(items=rows, total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}/role", response_model=UserPublic)
async def patch_user_role(
    user_id: uuid.UUID,
    body: SetRoleBody,
) -> UserPublic:
    user = await set_user_role(user_id, body.role)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserPublic(
        id=user.id,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
        last_seen_at=user.last_seen_at.isoformat(),
        source="email_code",
    )


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


@router.patch("/settings", response_model=AppSettingsPublic)
async def patch_settings(
    body: AppSettingsPatch,
    current_user: RequiredAdmin,
) -> AppSettingsPublic:
    row = await update_app_settings(
        body.model_dump(exclude_unset=True), updated_by=current_user.id
    )
    return to_app_settings_public(row)


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
    return to_app_settings_public(row)


@router.delete("/settings/logo", response_model=AppSettingsPublic)
async def remove_logo(current_user: RequiredAdmin) -> AppSettingsPublic:
    row = await update_app_settings(
        {"logo": None, "logo_content_type": None}, updated_by=current_user.id
    )
    return to_app_settings_public(row)
