import uuid
from datetime import datetime

from backend.config import settings
from utils.database.models.app_settings import AppSettings, AppSettingsPublic
from utils.database.session import get_session
from utils.storage.redis import REDIS_APP_SETTINGS_KEY, invalidate_cache, redis_cache

_DEFAULTS = AppSettings(
    auth_access_policy=settings.AUTH_ACCESS_POLICY,
    auth_domain_allowlist=settings.AUTH_DOMAIN_ALLOWLIST,
    votes_objective=settings.VOTES_OBJECTIVE,
)


def to_app_settings_public(row: AppSettings) -> AppSettingsPublic:
    return AppSettingsPublic(
        auth_access_policy=row.auth_access_policy,
        auth_domain_allowlist=row.auth_domain_allowlist,
        votes_objective=row.votes_objective,
        platform_name=row.platform_name,
        has_custom_logo=row.logo is not None,
        terms_content=row.terms_content,
        updated_at=row.updated_at.isoformat(),
        updated_by=row.updated_by,
    )


@redis_cache(REDIS_APP_SETTINGS_KEY)
async def get_app_settings() -> AppSettings:
    if not settings.COMPARIA_DB_URI:
        return _DEFAULTS
    async with get_session() as session:
        return await session.get(AppSettings, 1) or _DEFAULTS


async def update_app_settings(patch: dict, updated_by: uuid.UUID) -> AppSettings:
    async with get_session() as session:
        row = await session.get(AppSettings, 1)
        if not row:
            row = AppSettings(id=1)

        for key, value in patch.items():
            setattr(row, key, value)
        row.updated_at = datetime.now()
        row.updated_by = updated_by

        session.add(row)
        await session.commit()
        await session.refresh(row)

    invalidate_cache(REDIS_APP_SETTINGS_KEY)
    return row
