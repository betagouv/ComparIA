from fastapi import HTTPException, Request, status

from backend.auth.services import get_user_from_token
from utils.database.models.auth import User


async def require_admin(request: Request) -> User:
    token = request.cookies.get("auth_session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    return user
