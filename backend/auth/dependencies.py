from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from backend.auth.services import get_user_from_token
from utils.database.models.auth import User


# FIXME role should be a literal, update db model
async def optional_user(request: Request, role: str | None = None) -> User | None:
    token = request.cookies.get("auth_session")
    if not token:
        return None
    user = await get_user_from_token(token)
    if not user:
        return None
    if role and user.role != role:
        return None
    return user


# FIXME role should be a literal, update db model
async def require_user(request: Request, role: str | None = None) -> User:
    token = request.cookies.get("auth_session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if role and user.role != role:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user


async def require_admin(request: Request) -> User:
    return require_user(request, "admin")


OptionalUser = Annotated[User | None, Depends(optional_user)]
RequiredUser = Annotated[User, Depends(require_user)]
RequiredAdmin = Annotated[User, Depends(require_admin)]
