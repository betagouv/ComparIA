import logging
import time
from datetime import datetime
from types import SimpleNamespace
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from backend.admin.activity import router as admin_activity_router
from backend.admin.dataset_check import router as admin_dataset_check_router
from backend.admin.legal import router as admin_legal_router
from backend.admin.llms import admin_llms_router
from backend.admin.publishing import router as admin_publishing_router
from backend.admin.suggestions import router as admin_suggestions_router
from backend.admin.survey import router as admin_survey_router
from backend.admin.tools import admin_tools_router
from backend.admin.users import admin_users_router
from backend.admin.vote_tags import router as admin_vote_tags_router
from backend.arena.checks import (
    list_decision_models,
    read_cached_scores,
    score_prompt,
    verdict,
    write_cached_scores,
)
from backend.auth.dependencies import RequiredAdmin, require_admin
from backend.auth.oidc import (
    check_oidc_connection,
    connection_test_passed,
    oidc_available,
    oidc_config_fingerprint,
)
from backend.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    INSTANCE_LOGO_BOX,
    OIDC_LOGO_BOX,
    settings,
)
from backend.utils.logos import read_logo
from utils.database.models.app_settings import (
    AppSettings,
    AppSettingsPatch,
    AppSettingsPublic,
    OIDCConnectionTest,
)
from utils.database.models.prompt_check import (
    Criteria,
    Description,
    PromptCheck,
    PromptCheckStatus,
    PromptCheckUpsert,
)
from utils.database.prompt_checks import (
    UNHEALTHY_AFTER_FAILURES,
    get_consecutive_failures,
    get_prompt_check,
    get_prompt_check_stats,
    get_warnings_shown,
    is_key_rejected,
    is_out_of_credits,
    update_prompt_check,
)
from utils.database.settings import get_app_settings, update_app_settings
from utils.secrets import encrypt_secret
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(
    prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)]
)

router.include_router(admin_activity_router)
router.include_router(admin_legal_router)
router.include_router(admin_llms_router)
router.include_router(admin_suggestions_router)
router.include_router(admin_survey_router)
router.include_router(admin_vote_tags_router)
router.include_router(admin_publishing_router)
router.include_router(admin_dataset_check_router)
router.include_router(admin_tools_router)
router.include_router(admin_users_router)


def _current_connection_test(row: AppSettings) -> OIDCConnectionTest | None:
    """The stored connection test, unless the provider config changed since."""
    stored = row.oidc_connection_test
    if not stored or stored.get("fingerprint") != oidc_config_fingerprint(row):
        return None
    return OIDCConnectionTest(
        passed=stored["passed"],
        reason=stored.get("reason"),
        tested_at=stored["tested_at"],
    )


def _to_app_settings_public(row: AppSettings) -> AppSettingsPublic:
    return AppSettingsPublic(
        auth_access_policy=row.auth_access_policy,
        auth_domain_allowlist=row.auth_domain_allowlist,
        votes_objective=row.votes_objective,
        ranking_min_votes=row.ranking_min_votes,
        ranking_max_rank_spread=row.ranking_max_rank_spread,
        survey_reask_after_days=row.survey_reask_after_days,
        ranking_grey_rank_spread=row.ranking_grey_rank_spread,
        platform_name=row.platform_name,
        primary_color_light=row.primary_color_light,
        primary_color_dark=row.primary_color_dark,
        secondary_color_light=row.secondary_color_light,
        secondary_color_dark=row.secondary_color_dark,
        homepage_url=row.homepage_url,
        publish_frequency=row.publish_frequency,
        publish_hour=row.publish_hour,
        publish_timezone=row.publish_timezone,
        dataset_voter_ids=row.dataset_voter_ids,
        has_custom_logo=row.logo is not None,
        logo_version=row.logo_version,
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
        oidc_connection_test=_current_connection_test(row),
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
    patch = body.model_dump(exclude_unset=True)
    if "oidc_client_secret" in patch:
        secret = patch.pop("oidc_client_secret")
        # Same key as every other secret at rest; the column holds bytes.
        patch["oidc_client_secret_encrypted"] = (
            encrypt_secret(secret).encode() if secret else None
        )
    if "auth_methods" in patch or any(k.startswith("oidc_") for k in patch):
        current = await get_app_settings()
        effective_methods = patch.get("auth_methods", current.auth_methods)
        effective = SimpleNamespace(
            auth_methods=effective_methods,
            **{
                field: patch.get(field, getattr(current, field))
                for field in (
                    "oidc_issuer",
                    "oidc_client_id",
                    "oidc_client_secret_encrypted",
                    "oidc_scopes",
                    "oidc_connection_test",
                )
            },
        )
        if "oidc" in effective_methods and not oidc_available(effective):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "OIDC provider config (issuer, client_id, readable "
                    "client_secret, scopes including openid) must be complete "
                    "before enabling the oidc auth method."
                ),
            )
        # With the email code gone, SSO is the only way in: a config that was
        # never shown to work, or was edited since, would lock everyone out.
        if (
            "email_code" in current.auth_methods
            and "email_code" not in effective_methods
            and not connection_test_passed(effective)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Test the OIDC connection on the current provider config "
                    "before removing the email code sign-in."
                ),
            )
    row = await update_app_settings(patch, updated_by=current_user.id)
    return _to_app_settings_public(row)


@router.post("/settings/oidc/test", response_model=OIDCConnectionTest)
async def run_oidc_connection_test(current_user: RequiredAdmin) -> OIDCConnectionTest:
    """Check the stored OIDC provider config and remember the outcome for the
    config as it is now; editing the config makes the outcome stale."""
    row = await get_app_settings()
    reason = await check_oidc_connection(row)
    result = {
        "passed": reason is None,
        "reason": reason,
        "tested_at": datetime.now().isoformat(),
    }
    await update_app_settings(
        {
            "oidc_connection_test": {
                **result,
                "fingerprint": oidc_config_fingerprint(row),
            }
        },
        updated_by=current_user.id,
    )
    return OIDCConnectionTest(**result)


@router.put("/settings/logo", response_model=AppSettingsPublic)
async def upload_logo(
    current_user: RequiredAdmin,
    file: UploadFile,
) -> AppSettingsPublic:
    logo, content_type = await read_logo(file, INSTANCE_LOGO_BOX)
    row = await update_app_settings(
        {"logo": logo, "logo_content_type": content_type},
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
    logo, content_type = await read_logo(file, OIDC_LOGO_BOX)
    row = await update_app_settings(
        {"oidc_button_logo": logo, "oidc_button_logo_content_type": content_type},
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
    key_rejected = is_key_rejected()
    out_of_credits = is_out_of_credits()
    return PromptCheckStatus(
        enabled=row.enabled,
        has_api_key=bool(row.api_key),
        required=row.required,
        model=row.model,
        description=row.description,
        criteria=row.criteria,
        conversations_per_ip_per_hour=row.conversations_per_ip_per_hour,
        conversations_same_models_per_ip_per_hour=(
            row.conversations_same_models_per_ip_per_hour
        ),
        updated_at=row.updated_at.isoformat(),
        updated_by=row.updated_by,
        consecutive_failures=failures,
        key_rejected=key_rejected,
        out_of_credits=out_of_credits,
        no_api_key=not (row.api_key or settings.OPENROUTER_API_KEY),
        no_model=not row.model,
        healthy=(
            failures < UNHEALTHY_AFTER_FAILURES
            and not key_rejected
            and not out_of_credits
        ),
        warnings_shown=get_warnings_shown(),
        default_conversations_per_ip_per_hour=(
            settings.RATELIMIT_CONVERSATIONS_PER_IP_PER_HOUR
        ),
        default_conversations_same_models_per_ip_per_hour=(
            settings.RATELIMIT_CONVERSATIONS_SAME_MODELS_PER_IP_PER_HOUR
        ),
    )


@router.get("/prompt-check", response_model=PromptCheckStatus)
async def read_prompt_check() -> PromptCheckStatus:
    return _to_prompt_check_status(await get_prompt_check())


@router.get("/prompt-check/schema")
async def read_prompt_check_schema():
    return PromptCheckUpsert.model_json_schema(schema_generator=FormJsonSchema)


@router.put("/prompt-check", response_model=PromptCheckStatus)
async def put_prompt_check(
    body: PromptCheckUpsert,
    current_user: RequiredAdmin,
) -> PromptCheckStatus:
    data = body.model_dump(exclude={"api_key"})
    # A blank key keeps the stored one, as on the endpoint form.
    if api_key := (body.api_key or "").strip():
        data["api_key"] = api_key
    row = await update_prompt_check(data, updated_by=current_user.id)
    return _to_prompt_check_status(row)


@router.delete("/prompt-check/api-key", response_model=PromptCheckStatus)
async def delete_prompt_check_api_key(current_user: RequiredAdmin) -> PromptCheckStatus:
    """Forget the stored key, so the check falls back to OPENROUTER_API_KEY."""
    row = await update_prompt_check({"api_key": None}, updated_by=current_user.id)
    return _to_prompt_check_status(row)


# Keys the admin page translates, like the verdict messages from `checks`.
NO_API_KEY_MESSAGE = "no_api_key"
NO_MODEL_MESSAGE = "no_model"
CALL_FAILED_MESSAGE = "call_failed"


class PromptCheckTryBody(BaseModel):
    """A prompt plus, when the admin is trying edits they have not saved, the
    configuration to judge it against. Each field falls back to the stored row."""

    text: str = Field(min_length=1, max_length=BLIND_MODE_INPUT_CHAR_LEN_LIMIT)
    criteria: Criteria | None = None
    description: Description | None = None
    model: str | None = Field(default=None, min_length=1, max_length=100)


class PromptCheckTryResult(BaseModel):
    decision: str
    scores: dict[str, float]
    triggered: dict[str, str]
    message: str | None
    latency_ms: int
    # What the decision model said when `decision` is "error".
    error: str | None = None


@router.post("/prompt-check/try", response_model=PromptCheckTryResult)
async def try_prompt_check(body: PromptCheckTryBody) -> PromptCheckTryResult:
    """Judge one prompt without touching anything the arena counts.

    No turn is written, no warning is counted and the failure streak is left
    alone, so trying a configuration cannot move the numbers the same page
    reports. Scores are cached on the questions and prompt text, not on the
    verdict, so trying several thresholds on the same text costs one check.
    """
    stored = await get_prompt_check()
    check = PromptCheck(
        id=stored.id,
        model=body.model or stored.model,
        description=(
            stored.description if body.description is None else body.description
        ),
        criteria=(
            stored.criteria
            if body.criteria is None
            else [c.model_dump() for c in body.criteria]
        ),
    )

    # A dry run ignores the on/off switch on purpose: trying a rule before
    # switching the check on is the main reason this exists.
    api_key = stored.api_key or settings.OPENROUTER_API_KEY
    missing = (
        NO_MODEL_MESSAGE
        if not check.model
        else NO_API_KEY_MESSAGE if not api_key else None
    )
    if missing:
        return PromptCheckTryResult(
            decision="error",
            scores={},
            triggered={},
            message=missing,
            latency_ms=0,
        )

    started = time.monotonic()
    scores = read_cached_scores(body.text, check)
    if scores is None:
        try:
            scores = await score_prompt(body.text, check, api_key)
        except Exception as e:
            return PromptCheckTryResult(
                decision="error",
                scores={},
                triggered={},
                message=CALL_FAILED_MESSAGE,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=str(e),
            )
        latency_ms = int((time.monotonic() - started) * 1000)
        write_cached_scores(body.text, check, scores)
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


class PromptCheckModel(BaseModel):
    id: str
    name: str


@router.get("/prompt-check/models", response_model=list[PromptCheckModel])
async def read_prompt_check_models() -> list[PromptCheckModel]:
    return [PromptCheckModel(**model) for model in await list_decision_models()]


class PromptCheckStats(BaseModel):
    period: str
    bucket: str
    historical_total: int
    total: int
    by_decision: dict[str, int]
    by_criterion: dict[str, dict[str, int]]
    timeline: list[dict]


@router.get("/prompt-check/stats", response_model=PromptCheckStats)
async def read_prompt_check_stats(
    period: Literal["all", "7d", "30d", "90d", "365d"] = Query(default="all"),
) -> PromptCheckStats:
    """Historical total and period-filtered activity.

    `by_criterion` counts the turns each criterion triggered on, so one turn can
    count in several. The timeline uses daily, weekly or monthly buckets based
    on the selected period.
    """
    return PromptCheckStats(**await get_prompt_check_stats(period))
