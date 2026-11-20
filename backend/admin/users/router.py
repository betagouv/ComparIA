import logging
import uuid

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from backend.admin.users.services import (
    CannotDeleteLastAdminError,
    CannotDeleteSelfError,
    CannotDemoteLastAdminError,
    CannotResetOwnTotpError,
    EmailAlreadyExistsError,
    cancel_user_invite,
    create_user,
    delete_user,
    get_user,
    list_users,
    reset_user_totp,
    update_user,
)
from backend.auth.dependencies import RequiredAdmin
from backend.auth.email import send_invite_link
from backend.auth.services import create_invite
from backend.config import settings
from utils.database.models.auth import NormalizedEmail, UserPublic, UserUpsert
from utils.database.settings import get_app_settings
from utils.i18n import SupportedLocale
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(prefix="/users", tags=["users"])


class UsersPage(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int


class InviteBody(BaseModel):
    email: NormalizedEmail
    # The inviting admin's language: the best guess we have for the invitee's.
    locale: SupportedLocale | None = None


@router.get("", response_model=UsersPage)
async def get_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> UsersPage:
    rows, total = await list_users(search=search, page=page, page_size=page_size)
    return UsersPage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/schema")
async def get_user_schema():
    return UserUpsert.model_json_schema(schema_generator=FormJsonSchema)


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user_route(body: UserUpsert) -> UserPublic:
    try:
        return await create_user(body)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@router.get("/{user_id}", response_model=UserPublic)
async def get_user_route(user_id: uuid.UUID) -> UserPublic:
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user


@router.put("/{user_id}", response_model=UserPublic)
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
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


@router.post("/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_user(
    body: InviteBody,
    current_user: RequiredAdmin,
) -> None:
    token = await create_invite(body.email, invited_by=current_user.id)
    link = f"{settings.COMPARIA_APP_URL}/invite/{token}"
    app_settings = await get_app_settings()
    await send_invite_link(
        body.email,
        link,
        platform_name=app_settings.platform_name,
        primary_color=app_settings.primary_color_light,
        secondary_color=app_settings.secondary_color_light,
        locale=body.locale or app_settings.default_locale,
    )


@router.delete("/{user_id}/invite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_invite(user_id: uuid.UUID) -> None:
    canceled = await cancel_user_invite(user_id)
    if not canceled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.delete("/{user_id}/totp", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_totp(user_id: uuid.UUID, current_user: RequiredAdmin) -> None:
    try:
        reset = await reset_user_totp(user_id, current_user.id)
    except CannotResetOwnTotpError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Change your own authenticator from your account page",
        )
    if not reset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # Who reset whom is worth a line in the log: the target's next sign-in
    # needs only an email code until they enrol again.
    logger.info(f"[AUTH] TOTP reset for user {user_id} by admin {current_user.id}")
