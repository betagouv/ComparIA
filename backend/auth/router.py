import logging
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.arena.captcha import verify_altcha_token
from backend.auth.dependencies import (
    RequiredAnomymous,
    RequiredUser,
    anonymous_session_token,
)
from backend.auth.email import send_login_code
from backend.auth.encryption import decrypt_oidc_secret
from backend.auth.export import AccountDataExport, build_account_export
from backend.auth.oidc import (
    build_authorization_url,
    consume_state,
    discover_provider,
    exchange_code_for_claims,
    oidc_callback_url,
)
from backend.auth.services import (
    _hash,
    accept_invite,
    erase_user_account,
    get_anonymous_consent_status,
    get_consent_status,
    get_invite_token_info,
    get_user_from_token,
    has_current_terms_acceptance,
)
from backend.auth.services import oidc_login as oidc_login_service
from backend.auth.services import (
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
    methods: list[Literal["email_code", "oidc"]]
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
    # OIDC method description for the login page. `oidc_enabled` is derived
    # from the instance's `auth_methods` plus a complete provider config, so
    # the button only shows when OIDC would actually work.
    oidc_enabled: bool
    oidc_button_label: str | None
    oidc_has_button_logo: bool


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
    oidc_enabled = (
        _oidc_configured(app_settings) and "oidc" in app_settings.auth_methods
    )
    return AuthConfig(
        access_policy=app_settings.auth_access_policy,
        methods=app_settings.auth_methods,
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
        oidc_enabled=oidc_enabled,
        oidc_button_label=app_settings.oidc_button_label,
        oidc_has_button_logo=app_settings.oidc_button_logo is not None,
    )


def _oidc_configured(app_settings) -> bool:
    """An instance can actually use OIDC only with a complete provider config."""
    return bool(
        app_settings.oidc_issuer
        and app_settings.oidc_client_id
        and app_settings.oidc_client_secret_encrypted is not None
    )


@router.get("/config/logo")
async def get_config_logo() -> Response:
    app_settings = await get_app_settings()
    if not app_settings.logo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        content=app_settings.logo,
        media_type=app_settings.logo_content_type or "image/png",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/config/oidc/logo")
async def get_config_oidc_logo() -> Response:
    """The OIDC button logo, served publicly so the login page can render it.

    The boolean `oidc_has_button_logo` in `/auth/config` only says *whether* a
    custom logo exists; this endpoint serves the bytes. Mirrors the platform
    logo endpoint above.
    """
    app_settings = await get_app_settings()
    if not app_settings.oidc_button_logo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return Response(
        content=app_settings.oidc_button_logo,
        media_type=app_settings.oidc_button_logo_content_type or "image/png",
        headers={"Cache-Control": "public, max-age=300"},
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
        anonymous_user_hash=_anonymous_hash(request),
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


@router.get("/oidc/login")
async def oidc_login(request: Request) -> RedirectResponse:
    """Redirect the browser to the instance's configured OIDC provider.

    Mirrors the email flow's ordering: the cheap, local gates (OIDC enabled
    and fully configured, terms accepted) run before any network call to the
    provider, so an unaccepted-terms flood never reaches discovery.
    """
    app_settings = await get_app_settings()
    if "oidc" not in app_settings.auth_methods or not _oidc_configured(app_settings):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OIDC is not enabled for this instance.",
        )

    anonymous_user_hash = _anonymous_hash(request)
    if not anonymous_user_hash or not await has_current_terms_acceptance(
        user_id=None, anonymous_user_hash=anonymous_user_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Accept the terms in force before signing in.",
        )

    discovery = await discover_provider(app_settings.oidc_issuer)
    authorization_endpoint = discovery.get("authorization_endpoint")
    if not authorization_endpoint:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="OIDC provider discovery document has no authorization_endpoint.",
        )
    authorization_url = build_authorization_url(
        authorization_endpoint=authorization_endpoint,
        client_id=app_settings.oidc_client_id,
        scopes=app_settings.oidc_scopes,
    )
    return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)


def _login_error(reason: str) -> RedirectResponse:
    """Redirect back to the login page with a machine-readable `error` param.

    The callback is reached via a redirect from the identity provider, so every
    failure mode resolves to a redirect (not an HTTPException): a bare error
    page is a dead end for a user who arrived mid-flow. The login page renders
    the `error` param. No session cookie is set on this path, so no partial
    auth state survives the failure.
    """
    return RedirectResponse(
        url=f"/login?{urlencode({'error': reason})}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/oidc/callback")
async def oidc_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Complete the OIDC round trip and sign the user in.

    Mirrors the email-code flow's ordering: the cheap local gate (state
    validated against what `oidc_login` stored), then the network call to the
    provider, then the domain-allowlist check, then the same session mint and
    `auth_session` cookie as email login. The OIDC tokens are consumed inside
    `exchange_code_for_claims` and never persisted.

    Every failure mode redirects back to `/login?error=...` instead of raising
    an `HTTPException`: the user arrives here mid-flow from the identity
    provider, so a JSON error page is a dead end. A failure never reaches
    `oidc_login`, so no `User` row is created and no session is minted — the
    round trip leaves no partial state behind.
    """
    app_settings = await get_app_settings()
    if "oidc" not in app_settings.auth_methods or not _oidc_configured(app_settings):
        return _login_error("oidc_unavailable")

    # The provider redirected back with an `error` param (OAuth2 standard) —
    # the user denied consent, or the provider rejected the request. There is
    # no code to exchange, and no point consuming state: bail out cleanly.
    if error:
        return _login_error("provider_error")

    stored_nonce = consume_state(state) if state else None
    if not stored_nonce:
        return _login_error("invalid_state")
    if not code:
        return _login_error("missing_code")

    try:
        discovery = await discover_provider(app_settings.oidc_issuer)
    except Exception:
        logger.exception("[OIDC] discovery failed during callback")
        return _login_error("provider_error")
    token_endpoint = discovery.get("token_endpoint")
    userinfo_endpoint = discovery.get("userinfo_endpoint")
    if not token_endpoint or not userinfo_endpoint:
        return _login_error("provider_error")

    client_secret = decrypt_oidc_secret(app_settings.oidc_client_secret_encrypted)
    try:
        claims = await exchange_code_for_claims(
            token_endpoint=token_endpoint,
            userinfo_endpoint=userinfo_endpoint,
            client_id=app_settings.oidc_client_id,
            client_secret=client_secret,
            code=code,
            redirect_uri=oidc_callback_url(),
        )
    except Exception:
        # The token endpoint rejects denied/expired/reused codes with a 4xx;
        # the userinfo endpoint can fail mid-flight. Either way the round trip
        # is unrecoverable from the browser's point of view.
        logger.exception("[OIDC] code exchange or userinfo retrieval failed")
        return _login_error("provider_error")

    if not claims.get("nonce") or claims["nonce"] != stored_nonce:
        return _login_error("invalid_nonce")

    email = claims.get("email")
    if not email:
        return _login_error("no_email")

    if app_settings.auth_domain_allowlist:
        domain = email.split("@")[-1].lower()
        if domain not in [d.lower() for d in app_settings.auth_domain_allowlist]:
            return _login_error("domain_not_allowed")

    ip = get_ip(request)
    user_agent = request.headers.get("user-agent")
    visitor_id = get_matomo_tracker_from_cookies(request.cookies)
    token = await oidc_login_service(
        email=email,
        ip=ip,
        user_agent=user_agent,
        visitor_id=visitor_id,
        anonymous_user_hash=_anonymous_hash(request),
    )

    redirect = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    redirect.set_cookie(
        "auth_session",
        token,
        httponly=True,
        secure=not settings.LANGUIA_DEBUG,
        samesite="lax",
        max_age=settings.AUTH_SESSION_LENGTH_DAYS * 86400,
    )
    return redirect


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
