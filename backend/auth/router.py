import logging
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.arena.captcha import verify_altcha_token
from backend.auth.dependencies import (
    RequiredAnomymous,
    RequiredUser,
    anonymous_session_token,
)
from backend.auth.email import send_login_code
from backend.auth.export import AccountDataExport, build_account_export
from backend.auth.services import (
    _hash,
    accept_invite,
    erase_user_account,
    get_anonymous_consent_status,
    get_consent_status,
    get_invite_token_info,
    get_user_from_token,
    has_current_terms_acceptance,
    record_anonymous_consent,
    record_user_consent,
    request_login_code,
    revoke_all_user_sessions,
    revoke_current_session,
    verify_login_code,
)
from backend.config import settings
from backend.settings.legal import LEGAL_LOCALE_PATTERN, get_active_legal_document
from backend.utils.user import get_ip, get_matomo_tracker_from_cookies
from utils.database.models.auth import LegalDocument
from utils.database.models.utils import as_naive_utc
from utils.database.settings import get_app_settings
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
    platform_name: str
    primary_color_light: str
    primary_color_dark: str
    secondary_color_light: str
    secondary_color_dark: str
    homepage_url: str | None
    platform_url: str
    has_custom_logo: bool
    enabled_locales: list[str]
    default_locale: str


class EmailRequestBody(BaseModel):
    email: EmailStr
    altcha_payload: str


class EmailVerifyBody(BaseModel):
    email: EmailStr
    code: str


class InviteStatus(BaseModel):
    valid: bool


class InviteAcceptBody(BaseModel):
    token: str


class ConsentAssertion(BaseModel):
    """What the visitor says they accepted, checked against the live document."""

    model_config = ConfigDict(extra="forbid")

    terms_version: str = Field(min_length=1, max_length=64)
    terms_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_at: datetime
    locale: str = Field(
        min_length=2, max_length=16, pattern=f"^{LEGAL_LOCALE_PATTERN.pattern}$"
    )
    legal_information_acknowledged: Literal[True]

    @field_validator("accepted_at")
    @classmethod
    def acceptance_must_be_recent_and_zoned(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("accepted_at must include a timezone")
        now = datetime.now(timezone.utc)
        accepted = value.astimezone(timezone.utc)
        if accepted < now - timedelta(minutes=30) or accepted > now + timedelta(
            minutes=5
        ):
            raise ValueError("accepted_at must reflect the current consent interaction")
        return as_naive_utc(accepted)


class ConsentBody(BaseModel):
    consent: ConsentAssertion


def _anonymous_hash(request: Request) -> str | None:
    token = anonymous_session_token(request)
    return _hash(token) if token else None


def _reject_cross_site(request: Request) -> None:
    """Refuse a state-changing auth POST driven by another site.

    Browsers send Origin on these, so a value that is neither ours nor the app's
    means a third-party page is trying to sign the visitor in, or out, without
    them asking. No Origin at all means a non-browser client, which is allowed.
    """
    origin = request.headers.get("origin")
    if not origin:
        return
    own_origin = f"{request.url.scheme}://{request.url.netloc}"
    if origin.rstrip("/") not in (settings.COMPARIA_APP_URL, own_origin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-site request rejected.",
        )


async def _validated_terms(assertion: ConsentAssertion) -> LegalDocument:
    document = await get_active_legal_document("terms", assertion.locale)
    if (
        not document
        or document.version != assertion.terms_version
        or document.content_hash != assertion.terms_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Terms have changed, read the version in force before continuing.",
        )
    return document


@router.get("/config")
async def get_config() -> AuthConfig:
    app_settings = await get_app_settings()
    return AuthConfig(
        access_policy=app_settings.auth_access_policy,
        methods=["email_code"],
        smtp_configured=bool(settings.SMTP_HOST),
        domain_allowlist=app_settings.auth_domain_allowlist,
        platform_name=app_settings.platform_name,
        primary_color_light=app_settings.primary_color_light,
        primary_color_dark=app_settings.primary_color_dark,
        secondary_color_light=app_settings.secondary_color_light,
        secondary_color_dark=app_settings.secondary_color_dark,
        homepage_url=app_settings.homepage_url,
        platform_url=settings.COMPARIA_APP_URL,
        has_custom_logo=app_settings.logo is not None,
        enabled_locales=app_settings.enabled_locales,
        default_locale=app_settings.default_locale,
    )


@router.get("/config/logo")
async def get_config_logo() -> Response:
    app_settings = await get_app_settings()
    if not app_settings.logo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        content=app_settings.logo,
        media_type=app_settings.logo_content_type or "image/png",
        headers={
            "Cache-Control": "public, max-age=300",
            # The logo can be an SVG, and an SVG can carry a <script>. Pages
            # only ever show it in an <img>, where scripts never run, but
            # opening this URL directly would render it as a document on our
            # own origin. sandbox puts it in an opaque origin with scripting
            # off, which leaves <img> untouched.
            "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
            "Content-Disposition": "inline",
        },
    )


@router.post("/email/request", status_code=status.HTTP_204_NO_CONTENT)
async def email_request(body: EmailRequestBody, request: Request) -> None:
    _reject_cross_site(request)
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

    app_settings = await get_app_settings()
    if app_settings.auth_domain_allowlist:
        domain = body.email.split("@")[-1].lower()
        if domain not in [d.lower() for d in app_settings.auth_domain_allowlist]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Email domain not allowed.",
            )

    # Checked after the cheap limits so an unaccepted flood is still throttled.
    anonymous_user_hash = _anonymous_hash(request)
    if not anonymous_user_hash or not await has_current_terms_acceptance(
        user_id=None, anonymous_user_hash=anonymous_user_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Accept the terms in force before requesting a login code.",
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
    _reject_cross_site(request)
    ip = get_ip(request)
    user_agent = request.headers.get("user-agent")
    visitor_id = get_matomo_tracker_from_cookies(request.cookies)
    email_hash = _hash(body.email)
    fail_key = REDIS_AUTH_VERIFY_FAIL.format(ip=ip, email=email_hash)
    # Same counter, keyed on the email alone: "*" is not a possible host, so the
    # two buckets never collide. Bounds guessing spread over many source IPs.
    email_fail_key = REDIS_AUTH_VERIFY_FAIL.format(ip="*", email=email_hash)

    try:
        client = get_redis_client()
        fail_count = client.get(fail_key)
        if fail_count and int(fail_count) >= settings.AUTH_VERIFY_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts, please request a new code.",
            )
        email_fail_count = client.get(email_fail_key)
        if (
            email_fail_count
            and int(email_fail_count) >= settings.AUTH_VERIFY_MAX_ATTEMPTS_PER_EMAIL
        ):
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
        anonymous_user_hash=_anonymous_hash(request),
    )
    if not token:
        try:
            client = get_redis_client()
            for key in (fail_key, email_fail_key):
                fail_count = client.incr(key)
                if fail_count == 1:
                    client.expire(key, 600)
        except Exception as e:
            logger.error(f"[AUTH] Redis rate limit check failed: {e}")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired code.",
        )

    try:
        client = get_redis_client()
        client.delete(fail_key)
        client.delete(email_fail_key)
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")

    response.set_cookie(
        "auth_session",
        token,
        httponly=True,
        secure=settings.COMPARIA_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.AUTH_SESSION_LENGTH_DAYS * 86400,
    )
    return {"email": body.email}


@router.get("/invite/{token}")
async def invite_status(token: str) -> InviteStatus:
    # Only whether the link still works: the invited address is not the token
    # holder's to read, and an invite link travels through mailboxes and logs.
    info = await get_invite_token_info(token)
    return InviteStatus(valid=bool(info))


@router.post("/invite/accept")
async def invite_accept(
    body: InviteAcceptBody, request: Request, response: Response
) -> dict:
    _reject_cross_site(request)
    # Nothing cheap to run first, unlike the login route, and accept_invite
    # spends the token, so a refusal has to come before it.
    anonymous_user_hash = _anonymous_hash(request)
    if not anonymous_user_hash or not await has_current_terms_acceptance(
        user_id=None, anonymous_user_hash=anonymous_user_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Accept the terms in force before accepting an invitation.",
        )

    ip = get_ip(request)
    user_agent = request.headers.get("user-agent")
    visitor_id = get_matomo_tracker_from_cookies(request.cookies)

    token = await accept_invite(
        token=body.token,
        ip=ip,
        user_agent=user_agent,
        visitor_id=visitor_id,
        anonymous_user_hash=anonymous_user_hash,
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
        secure=settings.COMPARIA_COOKIE_SECURE,
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


@router.get("/me/export")
async def export_account_data(user: RequiredUser) -> AccountDataExport:
    return await build_account_export(user)


class AccountEraseBody(BaseModel):
    email: EmailStr


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def erase_account(
    body: AccountEraseBody, user: RequiredUser, response: Response
) -> None:
    # Retyping the address guards against a stray click, nothing more: the
    # session cookie is what says who is asking.
    if body.email.lower() != user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email confirmation does not match the signed-in account.",
        )
    await erase_user_account(user.id)
    response.delete_cookie("auth_session")


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(request: Request, response: Response) -> None:
    token = request.cookies.get("auth_session")
    if token:
        user = await get_user_from_token(token)
        if user:
            await revoke_all_user_sessions(user.id)
    response.delete_cookie("auth_session")


@router.post("/consent", status_code=status.HTTP_204_NO_CONTENT)
async def accept_consent(
    body: ConsentBody, user: RequiredUser, request: Request
) -> None:
    document = await _validated_terms(body.consent)
    await record_user_consent(
        user.id,
        document,
        body.consent.accepted_at,
        request.cookies.get("auth_session"),
    )


@router.get("/consent")
async def consent_status(user: RequiredUser) -> dict:
    return await get_consent_status(user.id)


@router.post("/consent/anonymous", status_code=status.HTTP_204_NO_CONTENT)
async def accept_anonymous_consent(
    body: ConsentBody, anonymous_user_hash: RequiredAnomymous
) -> None:
    document = await _validated_terms(body.consent)
    await record_anonymous_consent(
        anonymous_user_hash, document, body.consent.accepted_at
    )


@router.get("/consent/anonymous")
async def anonymous_consent_status(anonymous_user_hash: RequiredAnomymous) -> dict:
    return await get_anonymous_consent_status(anonymous_user_hash)
