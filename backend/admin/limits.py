import uuid

from fastapi import APIRouter

from backend.activity.services import QueryTimedOutError
from backend.arena import limits
from backend.arena.models import (
    AdminLimit,
    AdminLimits,
    AdminLimitsPatch,
    LimitsCalibration,
)
from backend.auth.dependencies import RequiredAdmin
from backend.errors import ActivityQueryTimeoutError
from utils.arena.calibrate import calibrate
from utils.database.models.app_settings import AppSettings
from utils.database.models.auth import User
from utils.database.session import get_session
from utils.database.settings import get_app_settings, update_limit_settings

router = APIRouter(prefix="/limits", tags=["limits"])


async def _email(user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    async with get_session() as session:
        user = await session.get(User, user_id)
    return user.email if user else None


async def _to_admin_limits(row: AppSettings) -> AdminLimits:
    stored = limits.stored_settings(row)
    return AdminLimits(
        limits=[
            AdminLimit(
                name=name,
                value=stored.get(name, limits.default(name)),
                default=limits.default(name),
                stored=name in stored,
            )
            for name in limits.LIMIT_SETTINGS
        ],
        updated_at=row.limits_updated_at,
        updated_by=await _email(row.limits_updated_by),
    )


@router.get("", response_model=AdminLimits)
async def read_limits() -> AdminLimits:
    return await _to_admin_limits(await get_app_settings())


@router.patch("", response_model=AdminLimits)
async def patch_limits(
    body: AdminLimitsPatch, current_user: RequiredAdmin
) -> AdminLimits:
    row = await update_limit_settings(
        body.model_dump(exclude_unset=True), updated_by=current_user.id
    )
    # In force at once on this process; the others read it within
    # `limits.RELOAD_SECONDS`.
    await limits.load_settings()
    return await _to_admin_limits(row)


@router.get("/calibration", response_model=LimitsCalibration)
async def read_calibration() -> LimitsCalibration:
    """Values proposed from the last week's comparisons. Read-only: nothing
    changes until the admin applies them."""
    try:
        return await calibrate()
    except QueryTimedOutError:
        raise ActivityQueryTimeoutError()
