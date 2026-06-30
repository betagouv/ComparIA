import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.auth.services import get_user_from_token
from backend.config import settings

logger = logging.getLogger("languia")

_AUTH_REQUIRED_RESPONSE = JSONResponse(
    {"detail": "Authentication required"}, status_code=401
)


async def auth_middleware(request: Request, call_next):
    if (
        settings.AUTH_ACCESS_POLICY == "sign_in_required"
        and request.url.path.startswith("/arena")
        and request.url.path != "/arena/challenge"
        and settings.COMPARIA_DB_URI
    ):
        token = request.cookies.get("auth_session")
        if not token:
            return _AUTH_REQUIRED_RESPONSE
        user = await get_user_from_token(token)
        if not user:
            return _AUTH_REQUIRED_RESPONSE

    return await call_next(request)
