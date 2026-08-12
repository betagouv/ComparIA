import time
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from backend.admin.llms import admin_llms_router
from backend.admin.publishing import router as admin_publishing_router
from backend.admin.services import (
    CannotDeleteLastAdminError,
    CannotDeleteSelfError,
    CannotDemoteLastAdminError,
    EmailAlreadyExistsError,
    cancel_user_invite,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)
from backend.admin.suggestions import router as admin_suggestions_router
from backend.admin.vote_tags import router as admin_vote_tags_router
from backend.arena.checks import (
    moderate,
    read_cached_scores,
    verdict,
    write_cached_scores,
)
from backend.auth.dependencies import RequiredAdmin, require_admin
from backend.auth.email import send_invite_link
from backend.auth.encryption import encrypt_oidc_secret
from backend.auth.services import create_invite
from backend.config import BLIND_MODE_INPUT_CHAR_LEN_LIMIT, settings
from backend.settings.informational_legal import (
    InformationalLegalPages,
    get_informational_legal_pages,
)
from backend.settings.legal import (
    DEFAULT_LEGAL_LANGUAGE,
    LEGAL_CONTENT_MAX_LENGTH,
    LEGAL_LOCALE_PATTERN,
    LEGAL_VERSION_MAX_LENGTH,
    SEEDED_TERMS_VERSION,
    DuplicateLegalDocumentError,
    InvalidEffectiveDateError,
    LegalPresentation,
    LocaleQuery,
    OptionalLocaleQuery,
    UtcTimestamp,
    get_active_legal_document,
    get_legal_presentation,
    list_legal_documents,
    publish_legal_document,
)
from utils.database.models.app_settings import (
    AppSettings,
    AppSettingsPatch,
    AppSettingsPublic,
)
from utils.database.models.auth import (
    LegalDocument,
    LegalDocumentKind,
    UserPublic,
    UserUpsert,
)
from utils.database.models.llms import LLMEndpoint
from utils.database.models.prompt_check import (
    PromptCheck,
    PromptCheckPatch,
    PromptCheckStatus,
    validate_categories,
)
from utils.database.prompt_checks import (
    UNHEALTHY_AFTER_FAILURES,
    get_consecutive_failures,
    get_prompt_check,
    get_prompt_check_stats,
    get_warnings_shown,
    update_prompt_check,
)
from utils.database.session import get_session
from utils.database.settings import get_app_settings, update_app_settings
from utils.utils import FormJsonSchema

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

router.include_router(admin_llms_router)
router.include_router(admin_suggestions_router)
router.include_router(admin_vote_tags_router)
router.include_router(admin_publishing_router)


class UsersPage(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int


class InviteBody(BaseModel):
    email: EmailStr


class AdminLegalDocument(BaseModel):
    id: uuid.UUID
    kind: LegalDocumentKind
    version: str
    locale: str
    content: str
    content_hash: str
    published_at: UtcTimestamp
    effective_at: UtcTimestamp
    retired_at: UtcTimestamp | None
    seeded: bool


class PublishLegalDocumentBody(BaseModel):
    version: str = Field(
        min_length=1, max_length=LEGAL_VERSION_MAX_LENGTH, pattern=r"^\S(?:.*\S)?$"
    )
    locale: str = Field(
        min_length=2,
        max_length=16,
        pattern=f"^{LEGAL_LOCALE_PATTERN.pattern}$",
    )
    content: str = Field(min_length=1, max_length=LEGAL_CONTENT_MAX_LENGTH)
    effective_at: datetime | None = None
    confirm_publication: Literal[True]


class UpdateLegalPresentationBody(BaseModel):
    presentation: LegalPresentation


@router.get("/legal/informational-pages", response_model=InformationalLegalPages)
async def get_admin_informational_legal_pages() -> InformationalLegalPages:
    return await get_informational_legal_pages()


@router.put("/legal/informational-pages", response_model=InformationalLegalPages)
async def put_admin_informational_legal_pages(
    body: InformationalLegalPages,
    current_user: RequiredAdmin,
) -> InformationalLegalPages:
    await update_app_settings(
        {"informational_legal_pages": body.pages.model_dump(mode="json")},
        updated_by=current_user.id,
    )
    return body


_LOGO_MAX_SIZE = 2 * 1024 * 1024
_LOGO_CONTENT_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp"}


def _to_admin_legal_document(row: LegalDocument) -> AdminLegalDocument:
    return AdminLegalDocument(
        id=row.id,
        kind=row.kind,
        version=row.version,
        locale=row.language,
        content=row.content,
        content_hash=row.content_hash,
        published_at=row.published_at,
        effective_at=row.effective_at,
        retired_at=row.retired_at,
        seeded=row.kind == "terms" and row.version == SEEDED_TERMS_VERSION,
    )


async def _current_legal_document(
    kind: LegalDocumentKind, locale: str
) -> AdminLegalDocument:
    document = await get_active_legal_document(kind, locale)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active document is available for this locale",
        )
    return _to_admin_legal_document(document)


async def _publish(
    kind: LegalDocumentKind, body: PublishLegalDocumentBody
) -> AdminLegalDocument:
    try:
        document = await publish_legal_document(
            kind=kind,
            version=body.version,
            language=body.locale,
            content=body.content,
            effective_at=body.effective_at,
        )
    except DuplicateLegalDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except (InvalidEffectiveDateError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    return _to_admin_legal_document(document)


@router.get("/legal/terms", response_model=list[AdminLegalDocument])
async def get_terms_publications(
    locale: OptionalLocaleQuery = None,
) -> list[AdminLegalDocument]:
    documents = await list_legal_documents("terms", locale)
    return [_to_admin_legal_document(document) for document in documents]


@router.get("/legal/terms/current", response_model=AdminLegalDocument)
async def get_current_terms(
    locale: LocaleQuery = DEFAULT_LEGAL_LANGUAGE,
) -> AdminLegalDocument:
    return await _current_legal_document("terms", locale)


@router.post(
    "/legal/terms",
    response_model=AdminLegalDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_terms_publication(
    body: PublishLegalDocumentBody,
) -> AdminLegalDocument:
    return await _publish("terms", body)


@router.get("/legal/privacy-policy", response_model=list[AdminLegalDocument])
async def get_privacy_policy_publications(
    locale: OptionalLocaleQuery = None,
) -> list[AdminLegalDocument]:
    documents = await list_legal_documents("privacy_policy", locale)
    return [_to_admin_legal_document(document) for document in documents]


@router.get("/legal/privacy-policy/current", response_model=AdminLegalDocument)
async def get_current_privacy_policy(
    locale: LocaleQuery = DEFAULT_LEGAL_LANGUAGE,
) -> AdminLegalDocument:
    return await _current_legal_document("privacy_policy", locale)


@router.post(
    "/legal/privacy-policy",
    response_model=AdminLegalDocument,
    status_code=status.HTTP_201_CREATED,
)
async def create_privacy_policy_publication(
    body: PublishLegalDocumentBody,
) -> AdminLegalDocument:
    return await _publish("privacy_policy", body)


@router.get("/legal/presentation", response_model=LegalPresentation)
async def get_participation_presentation() -> LegalPresentation:
    return await get_legal_presentation()


@router.put("/legal/presentation", response_model=LegalPresentation)
async def put_participation_presentation(
    body: UpdateLegalPresentationBody,
    current_user: RequiredAdmin,
) -> LegalPresentation:
    await update_app_settings(
        {"legal_presentation": body.presentation.model_dump(mode="json")},
        updated_by=current_user.id,
    )
    return body.presentation


@router.get("/users", response_model=UsersPage)
async def get_users(
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> UsersPage:
    rows, total = await list_users(search=search, page=page, page_size=page_size)
    return UsersPage(items=rows, total=total, page=page, page_size=page_size)


@router.get("/users/schema")
async def get_user_schema():
    return UserUpsert.model_json_schema(schema_generator=FormJsonSchema)


@router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
async def create_user_route(body: UserUpsert) -> UserPublic:
    try:
        return await create_user(body)
    except EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user_route(user_id: uuid.UUID) -> UserPublic:
    user = await get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user


@router.put("/users/{user_id}", response_model=UserPublic)
async def update_user_route(user_id: uuid.UUID, body: UserUpsert) -> UserPublic:
    try:
        user = await update_user(user_id, body)
    except CannotDemoteLastAdminError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the last remaining admin",
        )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user(
    user_id: uuid.UUID,
    current_user: RequiredAdmin,
) -> None:
    try:
        deleted = await delete_user(user_id, current_user.id)
    except CannotDeleteSelfError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    except CannotDeleteLastAdminError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last remaining admin",
        )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


@router.post("/users/invite", status_code=status.HTTP_204_NO_CONTENT)
async def invite_user(
    body: InviteBody,
    current_user: RequiredAdmin,
) -> None:
    token = await create_invite(body.email, invited_by=current_user.id)
    link = f"{settings.COMPARIA_APP_URL}/invite/{token}"
    await send_invite_link(body.email, link)


@router.delete("/users/{user_id}/invite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_invite(user_id: uuid.UUID) -> None:
    canceled = await cancel_user_invite(user_id)
    if not canceled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


def _to_app_settings_public(row: AppSettings) -> AppSettingsPublic:
    return AppSettingsPublic(
        auth_access_policy=row.auth_access_policy,
        auth_domain_allowlist=row.auth_domain_allowlist,
        votes_objective=row.votes_objective,
        platform_name=row.platform_name,
        primary_color_light=row.primary_color_light,
        primary_color_dark=row.primary_color_dark,
        secondary_color_light=row.secondary_color_light,
        secondary_color_dark=row.secondary_color_dark,
        homepage_url=row.homepage_url,
        analysis_endpoint_id=row.analysis_endpoint_id,
        analysis_model=row.analysis_model,
        publish_frequency=row.publish_frequency,
        publish_hour=row.publish_hour,
        publish_timezone=row.publish_timezone,
        has_custom_logo=row.logo is not None,
        enabled_locales=row.enabled_locales,
        default_locale=row.default_locale,
        auth_methods=row.auth_methods,
        oidc_issuer=row.oidc_issuer,
        oidc_client_id=row.oidc_client_id,
        oidc_has_client_secret=row.oidc_client_secret_encrypted is not None,
        oidc_scopes=row.oidc_scopes,
        oidc_button_label=row.oidc_button_label,
        oidc_has_button_logo=row.oidc_button_logo is not None,
        oidc_button_logo_content_type=row.oidc_button_logo_content_type,
        updated_at=row.updated_at.isoformat(),
        updated_by=row.updated_by,
    )


@router.get("/settings", response_model=AppSettingsPublic)
async def get_settings() -> AppSettingsPublic:
    row = await get_app_settings()
    return _to_app_settings_public(row)


@router.patch("/settings", response_model=AppSettingsPublic)
async def patch_settings(
    body: AppSettingsPatch,
    current_user: RequiredAdmin,
) -> AppSettingsPublic:
    if body.enabled_locales is not None or body.default_locale is not None:
        current = await get_app_settings()
        effective_locales = (
            body.enabled_locales
            if body.enabled_locales is not None
            else current.enabled_locales
        )
        effective_default = (
            body.default_locale
            if body.default_locale is not None
            else current.default_locale
        )
        if effective_default not in effective_locales:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Default locale must be part of the enabled locales",
            )
    if body.analysis_endpoint_id:
        async with get_session() as session:
            if not await session.get(LLMEndpoint, body.analysis_endpoint_id):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Unknown LLM endpoint",
                )
    patch = body.model_dump(exclude_unset=True)
    if "oidc_client_secret" in patch:
        secret = patch.pop("oidc_client_secret")
        patch["oidc_client_secret_encrypted"] = (
            encrypt_oidc_secret(secret) if secret else None
        )
    if "auth_methods" in patch or any(k.startswith("oidc_") for k in patch):
        current = await get_app_settings()
        effective_methods = patch.get("auth_methods", current.auth_methods)
        if "oidc" in effective_methods:
            issuer = patch.get("oidc_issuer", current.oidc_issuer)
            client_id = patch.get("oidc_client_id", current.oidc_client_id)
            secret_enc = patch.get(
                "oidc_client_secret_encrypted",
                current.oidc_client_secret_encrypted,
            )
            if not (issuer and client_id and secret_enc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "OIDC provider config (issuer, client_id, client_secret) "
                        "must be complete before enabling the oidc auth method."
                    ),
                )
    row = await update_app_settings(patch, updated_by=current_user.id)
    return _to_app_settings_public(row)


@router.put("/settings/logo", response_model=AppSettingsPublic)
async def upload_logo(
    current_user: RequiredAdmin,
    file: UploadFile,
) -> AppSettingsPublic:
    if file.content_type not in _LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}",
        )
    content = await file.read()
    if len(content) > _LOGO_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file is too large (max 2 MB)",
        )
    row = await update_app_settings(
        {"logo": content, "logo_content_type": file.content_type},
        updated_by=current_user.id,
    )
    return _to_app_settings_public(row)


@router.delete("/settings/logo", response_model=AppSettingsPublic)
async def remove_logo(current_user: RequiredAdmin) -> AppSettingsPublic:
    row = await update_app_settings(
        {"logo": None, "logo_content_type": None}, updated_by=current_user.id
    )
    return _to_app_settings_public(row)


@router.put("/settings/oidc-logo", response_model=AppSettingsPublic)
async def upload_oidc_logo(
    current_user: RequiredAdmin,
    file: UploadFile,
) -> AppSettingsPublic:
    if file.content_type not in _LOGO_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported content type: {file.content_type}",
        )
    content = await file.read()
    if len(content) > _LOGO_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Logo file is too large (max 2 MB)",
        )
    row = await update_app_settings(
        {
            "oidc_button_logo": content,
            "oidc_button_logo_content_type": file.content_type,
        },
        updated_by=current_user.id,
    )
    return _to_app_settings_public(row)


@router.delete("/settings/oidc-logo", response_model=AppSettingsPublic)
async def remove_oidc_logo(current_user: RequiredAdmin) -> AppSettingsPublic:
    row = await update_app_settings(
        {"oidc_button_logo": None, "oidc_button_logo_content_type": None},
        updated_by=current_user.id,
    )
    return _to_app_settings_public(row)


def _to_prompt_check_status(row: PromptCheck) -> PromptCheckStatus:
    failures = get_consecutive_failures()
    return PromptCheckStatus(
        enabled=row.enabled,
        has_api_key=bool(row.api_key or settings.MISTRAL_API_KEY),
        model=row.model,
        categories=row.categories,
        updated_at=row.updated_at.isoformat(),
        updated_by=row.updated_by,
        consecutive_failures=failures,
        healthy=failures < UNHEALTHY_AFTER_FAILURES,
        warnings_shown=get_warnings_shown(),
    )


@router.get("/prompt-check", response_model=PromptCheckStatus)
async def read_prompt_check() -> PromptCheckStatus:
    return _to_prompt_check_status(await get_prompt_check())


@router.patch("/prompt-check", response_model=PromptCheckStatus)
async def patch_prompt_check(
    body: PromptCheckPatch,
    current_user: RequiredAdmin,
) -> PromptCheckStatus:
    patch = body.model_dump(exclude_unset=True)
    if "api_key" in patch:
        # Blanking the field clears the stored key and falls back to the
        # environment variable, rather than storing an empty string.
        patch["api_key"] = (patch["api_key"] or "").strip() or None
    row = await update_prompt_check(patch, updated_by=current_user.id)
    return _to_prompt_check_status(row)


NO_API_KEY_MESSAGE = (
    "Aucune clé API Mistral n'est configurée : la vérification ne peut pas "
    "s'exécuter."
)


class PromptCheckTryBody(BaseModel):
    """A prompt plus, when the admin is trying edits they have not saved, the
    configuration to judge it against. Both fields fall back to the stored row."""

    text: str = Field(min_length=1, max_length=BLIND_MODE_INPUT_CHAR_LEN_LIMIT)
    categories: dict[str, dict] | None = None
    model: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("categories", mode="before")
    @classmethod
    def check_categories(cls, value: object) -> dict[str, dict] | None:
        return None if value is None else validate_categories(value)


class PromptCheckTryResult(BaseModel):
    decision: str
    scores: dict[str, float]
    triggered: dict[str, str]
    message: str | None
    latency_ms: int


@router.post("/prompt-check/try", response_model=PromptCheckTryResult)
async def try_prompt_check(body: PromptCheckTryBody) -> PromptCheckTryResult:
    """Judge one prompt without touching anything the arena counts.

    No turn is written, no warning is counted and the failure streak is left
    alone, so trying a configuration cannot move the numbers the same page
    reports. Scores are cached on the model and prompt text, not on the verdict, so
    trying several thresholds on the same text costs one moderation call.
    """
    stored = await get_prompt_check()
    check = PromptCheck(
        id=stored.id,
        model=body.model or stored.model,
        categories=body.categories or stored.categories,
    )

    # A dry run ignores the on/off switch on purpose: trying a rule before
    # switching the check on is the main reason this exists.
    api_key = stored.api_key or settings.MISTRAL_API_KEY
    if not api_key:
        return PromptCheckTryResult(
            decision="error",
            scores={},
            triggered={},
            message=NO_API_KEY_MESSAGE,
            latency_ms=0,
        )

    started = time.monotonic()
    scores = read_cached_scores(body.text, check.model)
    if scores is None:
        try:
            scores = await moderate(body.text, check.model, api_key)
        except Exception as e:
            return PromptCheckTryResult(
                decision="error",
                scores={},
                triggered={},
                message=f"L'appel à Mistral a échoué : {e}",
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        latency_ms = int((time.monotonic() - started) * 1000)
        write_cached_scores(body.text, check.model, scores)
    else:
        latency_ms = 0

    result = verdict(check, scores, latency_ms)
    return PromptCheckTryResult(
        decision=result.decision,
        scores=result.scores,
        triggered=result.triggered,
        message=result.message,
        latency_ms=result.latency_ms,
    )


class PromptCheckStats(BaseModel):
    period: str
    bucket: str
    historical_total: int
    total: int
    by_decision: dict[str, int]
    by_category: dict[str, dict[str, int]]
    timeline: list[dict]


@router.get("/prompt-check/stats", response_model=PromptCheckStats)
async def read_prompt_check_stats(
    period: Literal["all", "7d", "30d", "90d", "365d"] = Query(default="all"),
) -> PromptCheckStats:
    """Historical total and period-filtered activity.

    `by_category` counts the turns each category triggered on, so one turn can
    count in several. The timeline uses daily, weekly or monthly buckets based
    on the selected period.
    """
    return PromptCheckStats(**await get_prompt_check_stats(period))
