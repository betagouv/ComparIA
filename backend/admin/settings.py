import logging
from datetime import datetime
from types import SimpleNamespace

from fastapi import APIRouter, HTTPException, UploadFile, status

from backend.auth.dependencies import RequiredAdmin
from backend.auth.oidc import (
    check_oidc_connection,
    connection_test_passed,
    oidc_available,
    oidc_config_fingerprint,
)
from backend.config import INSTANCE_LOGO_BOX, OIDC_LOGO_BOX
from backend.utils.logos import read_logo
from utils.database.models.app_settings import (
    AppSettings,
    AppSettingsPatch,
    AppSettingsPublic,
    OIDCConnectionTest,
)
from utils.database.settings import get_app_settings, update_app_settings
from utils.secrets import encrypt_secret

logger = logging.getLogger("languia")

router = APIRouter(prefix="/settings", tags=["settings"])


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
        cookie_banner_enabled=row.cookie_banner_enabled,
        matomo_enabled=row.matomo_enabled,
        matomo_url=row.matomo_url,
        matomo_site_id=row.matomo_site_id,
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


@router.get("", response_model=AppSettingsPublic)
async def get_settings() -> AppSettingsPublic:
    row = await get_app_settings()
    return _to_app_settings_public(row)


@router.patch("", response_model=AppSettingsPublic)
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
    if patch.keys() & {"matomo_enabled", "matomo_url", "matomo_site_id"}:
        current = await get_app_settings()
        # Judged on the row as it will be saved, so On alone takes the stored
        # address and id, and clearing one while On is refused.
        effective = {
            field: patch.get(field, getattr(current, field))
            for field in ("matomo_enabled", "matomo_url", "matomo_site_id")
        }
        if effective["matomo_enabled"] is True and not (
            effective["matomo_url"] and effective["matomo_site_id"]
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="matomo_needs_url_and_site_id",
            )
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


@router.post("/oidc/test", response_model=OIDCConnectionTest)
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


@router.put("/logo", response_model=AppSettingsPublic)
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


@router.delete("/logo", response_model=AppSettingsPublic)
async def remove_logo(current_user: RequiredAdmin) -> AppSettingsPublic:
    row = await update_app_settings(
        {"logo": None, "logo_content_type": None}, updated_by=current_user.id
    )
    return _to_app_settings_public(row)


@router.put("/oidc-logo", response_model=AppSettingsPublic)
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


@router.delete("/oidc-logo", response_model=AppSettingsPublic)
async def remove_oidc_logo(current_user: RequiredAdmin) -> AppSettingsPublic:
    row = await update_app_settings(
        {"oidc_button_logo": None, "oidc_button_logo_content_type": None},
        updated_by=current_user.id,
    )
    return _to_app_settings_public(row)
