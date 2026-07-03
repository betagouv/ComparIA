import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from backend.admin.llms.router import router as admin_llms_router
from backend.admin.services import delete_user, list_users, set_user_role
from backend.auth.dependencies import require_admin
from backend.auth.email import send_login_code
from backend.auth.services import request_login_code

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

router.include_router(admin_llms_router)


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    created_at: str
    last_seen_at: str
    source: str


class UsersPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class SetRoleBody(BaseModel):
    role: Literal["user", "admin"]


class InviteBody(BaseModel):
    email: str


@router.get("/users", response_model=UsersPage)
async def get_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> UsersPage:
    rows, total = await list_users(search=search, page=page, page_size=page_size)
    return UsersPage(
        items=[
            UserOut(
                id=row.id,
                email=row.email,
                role=row.role,
                created_at=row.created_at.isoformat(),
                last_seen_at=row.last_seen_at.isoformat(),
                source=row.source,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def patch_user_role(
    user_id: uuid.UUID,
    body: SetRoleBody,
) -> UserOut:
    user = await set_user_role(user_id, body.role)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserOut(
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
) -> None:
    deleted = await delete_user(user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/users/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_user(
    body: InviteBody,
) -> None:
    code = await request_login_code(body.email)
    await send_login_code(body.email, code)
