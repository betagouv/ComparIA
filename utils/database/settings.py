import logging
import uuid
from datetime import datetime

from sqlmodel import col, select

from backend.config import settings
from utils.database.models.app_settings import DEFAULT_ENABLED_LOCALES, AppSettings
from utils.database.models.llms import LLMData
from utils.database.session import get_session
from utils.storage.redis import (
    REDIS_APP_SETTINGS_KEY,
    REDIS_LLMS_DATA_CACHE_KEY,
    invalidate_cache,
    redis_cache,
)

logger = logging.getLogger("languia")

# The instance name happens to be a locale code on fr and da. One-off instances
# name themselves something else, so fall back to fr rather than seeding a
# locale the frontend can't render.
# Matched against the enabled set, not the supported one, to keep the default
# locale inside enabled_locales the way PATCH /admin/settings demands.
_INSTANCE_LOCALE = (
    settings.COMPARIA_INSTANCE_NAME
    if settings.COMPARIA_INSTANCE_NAME in DEFAULT_ENABLED_LOCALES
    else "fr"
)

_DEFAULTS = AppSettings(
    auth_access_policy=settings.AUTH_ACCESS_POLICY,
    auth_domain_allowlist=settings.AUTH_DOMAIN_ALLOWLIST,
    votes_objective=settings.VOTES_OBJECTIVE,
    default_locale=_INSTANCE_LOCALE,
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


async def update_limit_settings(
    changes: dict[str, float | None], updated_by: uuid.UUID
) -> AppSettings:
    """Store the model allowances in `changes`, None putting one back on its
    default, and log each change with the admin who made it."""
    async with get_session() as session:
        row = await session.get(AppSettings, 1)
        if not row:
            row = AppSettings(id=1)

        before = {name: getattr(row, f"limit_{name}") for name in changes}
        for name, value in changes.items():
            setattr(row, f"limit_{name}", value)
        row.limits_updated_at = datetime.now()
        row.limits_updated_by = updated_by

        session.add(row)
        await session.commit()
        await session.refresh(row)

    invalidate_cache(REDIS_APP_SETTINGS_KEY)
    for name, value in changes.items():
        if before[name] != value:
            logger.info(
                f"[LIMITS] {name} set from {_shown(before[name])} to "
                f"{_shown(value)} by admin {updated_by}"
            )
    return row


class UnknownLLMsError(Exception):
    """Daily caps sent for models the database does not hold."""

    def __init__(self, llm_ids: set[uuid.UUID]) -> None:
        super().__init__(", ".join(str(llm_id) for llm_id in sorted(llm_ids)))
        self.llm_ids = llm_ids


async def update_daily_caps(
    caps: dict[uuid.UUID, float | None], updated_by: uuid.UUID
) -> None:
    """Store the daily cap of each model in `caps`, None taking it off, and
    log each change with the admin who made it.

    Raises:
        UnknownLLMsError: with the ids no model has; nothing is stored
    """
    async with get_session() as session:
        rows = (
            await session.exec(select(LLMData).where(col(LLMData.id).in_(caps)))
        ).all()
        if unknown := set(caps) - {row.id for row in rows}:
            raise UnknownLLMsError(unknown)
        before = {row.id: (row.name, row.daily_usd_cap) for row in rows}
        for row in rows:
            row.daily_usd_cap = caps[row.id]
            session.add(row)
        await session.commit()

    invalidate_cache(REDIS_LLMS_DATA_CACHE_KEY)
    for llm_id, (name, cap) in before.items():
        if cap != caps[llm_id]:
            logger.info(
                f"[LIMITS] daily cap of {name} ({llm_id}) set from "
                f"{_cap(cap)} to {_cap(caps[llm_id])} by admin {updated_by}"
            )


def _cap(value: float | None) -> str:
    return "none" if value is None else f"${value:,.2f}"


def _shown(value: float | None) -> str:
    return "default" if value is None else f"{value:,}"
