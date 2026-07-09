import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from backend.arena.captcha import verify_altcha_token
from backend.auth.email import send_login_code
from backend.auth.services import (
    _hash,
    accept_invite,
    get_invite_token_info,
    get_user_from_token,
    request_login_code,
    revoke_all_user_sessions,
    revoke_current_session,
    verify_login_code,
)
from backend.config import settings
from backend.utils.user import get_ip, get_matomo_tracker_from_cookies
from utils.storage.redis import (
    REDIS_AUTH_EMAIL_REQ,
    REDIS_AUTH_EMAIL_REQ_EMAIL,
    REDIS_AUTH_VERIFY_FAIL,
    get_redis_client,
)

logger = logging.getLogger("languia")

router = APIRouter(prefix="/auth", tags=["auth"])


class AuthConfig(BaseModel):
    access_policy: Literal["anonymous_first", "sign_in_required"]
    methods: list[Literal["email_code"]]
    smtp_configured: bool
    domain_allowlist: list[str]


class EmailRequestBody(BaseModel):
    email: EmailStr
    altcha_payload: str


class EmailVerifyBody(BaseModel):
    email: EmailStr
    code: str


class InviteStatus(BaseModel):
    valid: bool
    email: str | None = None


class InviteAcceptBody(BaseModel):
    token: str


@router.get("/config")
async def get_config() -> AuthConfig:
    return AuthConfig(
        access_policy=settings.AUTH_ACCESS_POLICY,
        methods=["email_code"],
        smtp_configured=bool(settings.SMTP_HOST),
        domain_allowlist=settings.AUTH_DOMAIN_ALLOWLIST,
    )


@router.post("/email/request", status_code=status.HTTP_204_NO_CONTENT)
async def email_request(body: EmailRequestBody, request: Request) -> None:
    ip = get_ip(request)

    ok, error = verify_altcha_token(body.altcha_payload)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    try:
        client = get_redis_client()
        key = REDIS_AUTH_EMAIL_REQ.format(ip=ip)
        count = client.incr(key)
        if count == 1:
            client.expire(key, 3600)
        if count > settings.AUTH_EMAIL_REQUEST_PER_IP_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts, try again later.",
            )

        email_key = REDIS_AUTH_EMAIL_REQ_EMAIL.format(email=_hash(body.email))
        email_count = client.incr(email_key)
        if email_count == 1:
            client.expire(email_key, 3600)
        if email_count > settings.AUTH_EMAIL_REQUEST_PER_EMAIL_PER_HOUR:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts, try again later.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")

    if settings.AUTH_DOMAIN_ALLOWLIST:
        domain = body.email.split("@")[-1].lower()
        if domain not in [d.lower() for d in settings.AUTH_DOMAIN_ALLOWLIST]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email domain not allowed.",
            )

    code = await request_login_code(body.email)
    try:
        await send_login_code(body.email, code)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to send login code, please try again later.",
        )

    # A fresh code resets the verify attempt counter so a locked-out user can
    # retry. The per-email request cap above still bounds total guesses.
    try:
        get_redis_client().delete(
            REDIS_AUTH_VERIFY_FAIL.format(ip=ip, email=_hash(body.email))
        )
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")


@router.post("/email/verify")
async def email_verify(
    body: EmailVerifyBody, request: Request, response: Response
) -> dict:
    ip = get_ip(request)
    user_agent = request.headers.get("user-agent")
    visitor_id = get_matomo_tracker_from_cookies(request.cookies)
    fail_key = REDIS_AUTH_VERIFY_FAIL.format(ip=ip, email=_hash(body.email))

    try:
        client = get_redis_client()
        fail_count = client.get(fail_key)
        if fail_count and int(fail_count) >= settings.AUTH_VERIFY_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts, please request a new code.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")

    token = await verify_login_code(
        email=body.email,
        code=body.code,
        ip=ip,
        user_agent=user_agent,
        visitor_id=visitor_id,
    )
    if not token:
        try:
            client = get_redis_client()
            fail_count = client.incr(fail_key)
            if fail_count == 1:
                client.expire(fail_key, 600)
        except Exception as e:
            logger.error(f"[AUTH] Redis rate limit check failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code.",
        )

    try:
        get_redis_client().delete(fail_key)
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")

    response.set_cookie(
        "auth_session",
        token,
        httponly=True,
        secure=not settings.LANGUIA_DEBUG,
        samesite="lax",
        max_age=settings.AUTH_SESSION_LENGTH_DAYS * 86400,
    )
    return {"email": body.email}


@router.get("/invite/{token}")
async def invite_status(token: str) -> InviteStatus:
    info = await get_invite_token_info(token)
    if not info:
        return InviteStatus(valid=False)
    return InviteStatus(valid=True, email=info.email)


@router.post("/invite/accept")
async def invite_accept(
    body: InviteAcceptBody, request: Request, response: Response
) -> dict:
    ip = get_ip(request)
    user_agent = request.headers.get("user-agent")
    visitor_id = get_matomo_tracker_from_cookies(request.cookies)

    token = await accept_invite(
        token=body.token,
        ip=ip,
        user_agent=user_agent,
        visitor_id=visitor_id,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite link.",
        )

    response.set_cookie(
        "auth_session",
        token,
        httponly=True,
        secure=not settings.LANGUIA_DEBUG,
        samesite="lax",
        max_age=settings.AUTH_SESSION_LENGTH_DAYS * 86400,
    )
    return {"success": True}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    token = request.cookies.get("auth_session")
    if token:
        await revoke_current_session(token)
    response.delete_cookie("auth_session")


@router.get("/me")
async def get_me(request: Request) -> dict:
    token = request.cookies.get("auth_session")
    if not token:
        return {"user": None}
    user = await get_user_from_token(token)
    if not user:
        return {"user": None}
    return {"user": {"email": user.email, "role": user.role}}


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(request: Request, response: Response) -> None:
    token = request.cookies.get("auth_session")
    if token:
        user = await get_user_from_token(token)
        if user:
            await revoke_all_user_sessions(user.id)
    response.delete_cookie("auth_session")
