import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
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
    LoginResult,
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
from backend.auth.totp import (
    InvalidTotpCodeError,
    TotpChallengeExpiredError,
    TotpCodeRequiredError,
    TotpSetupMissingError,
    confirm_totp_setup,
    has_confirmed_totp,
    start_totp_setup,
    verify_totp_challenge,
)
from backend.config import settings
from backend.errors import RoleRequiredError
from backend.settings.legal import LEGAL_LOCALE_PATTERN, get_active_legal_document
from backend.utils.user import get_ip
from utils.database.models.auth import LegalDocument, User
from utils.database.models.utils import as_naive_utc
from utils.database.settings import get_app_settings
from utils.storage.redis import (
    REDIS_AUTH_EMAIL_REQ,
    REDIS_AUTH_EMAIL_REQ_EMAIL,
    REDIS_AUTH_TOTP_FAIL,
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
    # The language the visitor is reading the site in, for the email.
    locale: str | None = Field(default=None, min_length=2, max_length=16)


class EmailVerifyBody(BaseModel):
    email: EmailStr
    code: str


def _six_digits(value: str) -> str:
    value = re.sub(r"\s+", "", value)
    if not re.fullmatch(r"\d{6}", value):
        raise ValueError("code must be six digits")
    return value


class TotpCodeBody(BaseModel):
    code: str

    @field_validator("code")
    @classmethod
    def six_digits(cls, value: str) -> str:
        return _six_digits(value)


class TotpSetupBody(BaseModel):
    """`code` is only needed to replace an authenticator already in force."""

    code: str | None = None

    @field_validator("code")
    @classmethod
    def six_digits(cls, value: str | None) -> str | None:
        return _six_digits(value) if value else None


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    qr_svg: str


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


SESSION_COOKIE = "auth_session"
TOTP_CHALLENGE_COOKIE = "auth_totp_challenge"
_TOTP_CHALLENGE_COOKIE_MAX_AGE = 600


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        secure=settings.COMPARIA_COOKIE_SECURE,
        samesite="lax",
        max_age=settings.AUTH_SESSION_LENGTH_DAYS * 86400,
    )


def _set_login_cookie(response: Response, login: LoginResult) -> bool:
    """Hand the browser what the first factor earned; True when a second
    factor is still owed."""
    if login.kind == "session":
        _set_session_cookie(response, login.token)
        return False
    response.set_cookie(
        TOTP_CHALLENGE_COOKIE,
        login.token,
        httponly=True,
        secure=settings.COMPARIA_COOKIE_SECURE,
        samesite="lax",
        max_age=_TOTP_CHALLENGE_COOKIE_MAX_AGE,
    )
    return True


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
        await send_login_code(
            body.email,
            code,
            platform_name=app_settings.platform_name,
            primary_color=app_settings.primary_color_light,
            secondary_color=app_settings.secondary_color_light,
            locale=body.locale or app_settings.default_locale,
        )
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

    login = await verify_login_code(
        email=body.email,
        code=body.code,
        ip=ip,
        user_agent=user_agent,
        anonymous_user_hash=_anonymous_hash(request),
    )
    if not login:
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

    totp_required = _set_login_cookie(response, login)
    return {"email": body.email, "totp_required": totp_required}


@router.post("/totp/verify", response_model=None)
async def totp_verify(
    body: TotpCodeBody, request: Request, response: Response
) -> dict | JSONResponse:
    """Second factor of a sign-in that `/email/verify` or `/invite/accept`
    left half done. Attempts are counted on the challenge itself, so there
    is no Redis counter to keep here."""
    _reject_cross_site(request)
    challenge_token = request.cookies.get(TOTP_CHALLENGE_COOKIE)
    if not challenge_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in with your email code first.",
        )

    try:
        token = await verify_totp_challenge(
            token=challenge_token,
            code=body.code,
            ip=get_ip(request),
            user_agent=request.headers.get("user-agent"),
            anonymous_user_hash=_anonymous_hash(request),
        )
    except TotpChallengeExpiredError:
        # Headers set on `response` do not survive an HTTPException, and the
        # dead cookie has to go so the next sign-in starts clean.
        gone = JSONResponse(
            {"detail": "Sign-in expired, request a new email code."},
            status_code=status.HTTP_410_GONE,
        )
        gone.delete_cookie(TOTP_CHALLENGE_COOKIE)
        return gone
    except InvalidTotpCodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authenticator code.",
        )

    response.delete_cookie(TOTP_CHALLENGE_COOKIE)
    _set_session_cookie(response, token)
    user = await get_user_from_token(token)
    return {"email": user.email if user else None}


_TOTP_ENROL_MAX_FAILS = 10
_TOTP_ENROL_FAIL_TTL = 600


def _totp_enrol_guard(user_id: UUID) -> None:
    """Wrong codes while enrolling are bounded per account. Fail-open like the
    other Redis counters: a Redis outage must not lock admins out."""
    try:
        count = get_redis_client().get(REDIS_AUTH_TOTP_FAIL.format(user=user_id))
        if count and int(count) >= _TOTP_ENROL_MAX_FAILS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts, try again later.",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")


def _totp_enrol_failed(user_id: UUID) -> None:
    try:
        client = get_redis_client()
        key = REDIS_AUTH_TOTP_FAIL.format(user=user_id)
        if client.incr(key) == 1:
            client.expire(key, _TOTP_ENROL_FAIL_TTL)
    except Exception as e:
        logger.error(f"[AUTH] Redis rate limit check failed: {e}")


def _require_admin_role(user: User) -> None:
    # Not `require_admin`: that one also wants an enrolled authenticator,
    # which is the very thing these routes exist to set up.
    if user.role != "admin":
        raise RoleRequiredError("admin")


@router.post("/totp/setup")
async def totp_setup(
    body: TotpSetupBody, user: RequiredUser, response: Response
) -> TotpSetupResponse:
    _require_admin_role(user)
    _totp_enrol_guard(user.id)
    app_settings = await get_app_settings()
    try:
        setup = await start_totp_setup(user, body.code, app_settings.platform_name)
    except TotpCodeRequiredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="totp_code_required",
        )
    except InvalidTotpCodeError:
        _totp_enrol_failed(user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authenticator code.",
        )
    # The secret travels once, here. Nothing on the way may keep a copy.
    response.headers["Cache-Control"] = "no-store"
    return TotpSetupResponse(
        secret=setup.secret, otpauth_uri=setup.otpauth_uri, qr_svg=setup.qr_svg
    )


@router.post("/totp/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def totp_confirm(
    body: TotpCodeBody, user: RequiredUser, request: Request
) -> None:
    _require_admin_role(user)
    _totp_enrol_guard(user.id)
    try:
        await confirm_totp_setup(
            user, body.code, request.cookies.get(SESSION_COOKIE) or ""
        )
    except TotpSetupMissingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No authenticator waiting to be confirmed, start again.",
        )
    except InvalidTotpCodeError:
        _totp_enrol_failed(user.id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authenticator code.",
        )


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

    login = await accept_invite(
        token=body.token,
        ip=ip,
        user_agent=user_agent,
        anonymous_user_hash=anonymous_user_hash,
    )
    if not login:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invite link.",
        )

    totp_required = _set_login_cookie(response, login)
    return {"success": True, "totp_required": totp_required}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await revoke_current_session(token)
    response.delete_cookie(SESSION_COOKIE)
    response.delete_cookie(TOTP_CHALLENGE_COOKIE)


@router.get("/me")
async def get_me(request: Request) -> dict:
    token = request.cookies.get("auth_session")
    if not token:
        return {"user": None}
    user = await get_user_from_token(token)
    if not user:
        return {"user": None}
    return {
        "user": {
            "email": user.email,
            "role": user.role,
            "totp_enabled": await has_confirmed_totp(user.id),
        }
    }


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
