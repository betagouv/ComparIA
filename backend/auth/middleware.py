import logging
import secrets

from fastapi import Request

from backend.auth.services import get_user_from_token
from backend.config import ANONYMOUS_SESSION_COOKIE, settings
from backend.errors import AUTH_REQUIRED_RESPONSE
from utils.database.settings import get_app_settings

logger = logging.getLogger("languia")


async def auth_middleware(request: Request, call_next):
    app_settings = await get_app_settings()

    if (
        app_settings.auth_access_policy == "sign_in_required"
        and request.url.path.startswith("/arena")
        and request.url.path != "/arena/challenge"
        and settings.COMPARIA_DB_URI
    ):
        token = request.cookies.get("auth_session")
        if not token:
            return AUTH_REQUIRED_RESPONSE
        user = await get_user_from_token(token)
        if not user:
            return AUTH_REQUIRED_RESPONSE

    return await call_next(request)


async def anonymous_middleware(request: Request, call_next):
    response = await call_next(request)

    token = request.cookies.get(ANONYMOUS_SESSION_COOKIE)
    if not token:
        response.set_cookie(
            ANONYMOUS_SESSION_COOKIE,
            secrets.token_urlsafe(32),
            httponly=True,
            secure=not settings.LANGUIA_DEBUG,
            samesite="lax",
            max_age=settings.ANONYMOUS_SESSION_LENGTH_DAYS * 86400,
        )

    return response
