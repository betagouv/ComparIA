from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from backend.auth.services import _hash, get_user_from_token
from backend.config import ANONYMOUS_SESSION_COOKIE
from utils.database.models.auth import User, UserRole


async def optional_user(request: Request, role: UserRole | None = None) -> User | None:
    token = request.cookies.get("auth_session")
    if not token:
        return None
    user = await get_user_from_token(token)
    if not user:
        return None
    if role and user.role != role:
        return None
    return user


async def require_user(request: Request, role: UserRole | None = None) -> User:
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
    return await require_user(request, "admin")


async def require_anonymous(request: Request) -> str:
    token = request.cookies.get(ANONYMOUS_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    else:
        return _hash(token)


RequiredAnomymous = Annotated[str, Depends(require_anonymous)]
OptionalUser = Annotated[User | None, Depends(optional_user)]
RequiredUser = Annotated[User, Depends(require_user)]
RequiredAdmin = Annotated[User, Depends(require_admin)]
