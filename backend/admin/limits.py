import uuid
from typing import Iterable

from fastapi import APIRouter, HTTPException

from backend.activity.services import QueryTimedOutError
from backend.arena import limits
from backend.arena.models import (
    AdminLimit,
    AdminLimits,
    AdminLimitsPatch,
    LimitsCalibration,
    LLMDailyUsage,
)
from backend.auth.dependencies import RequiredAdmin
from backend.errors import ActivityQueryTimeoutError
from backend.llms.models import LLMDataEnabled
from utils.arena.calibrate import CALIBRATION_DAYS, calibrate, enabled_llms
from utils.database.models.app_settings import AppSettings
from utils.database.models.auth import User
from utils.database.session import get_session
from utils.database.settings import (
    UnknownLLMsError,
    get_app_settings,
    update_daily_caps,
    update_limit_settings,
)

router = APIRouter(prefix="/limits", tags=["limits"])


def daily_usage(llms: Iterable[LLMDataEnabled]) -> list[LLMDailyUsage]:
    """What each model spent today against its daily cap, the costliest
    first. Every model is counted, capped or not."""
    llms = list(llms)
    day = limits.Day.at()
    days = limits.read_model_days([llm.id for llm in llms], day)
    usage = [
        LLMDailyUsage(
            llm_id=llm.id,
            name=llm.name,
            input_chars=days[llm.id].sent,
            output_chars=days[llm.id].written,
            estimated_usd=days[llm.id].micro_usd / limits.MICRO_USD,
            cap_usd=llm.daily_usd_cap,
            resting=limits.is_resting(llm, days[llm.id]),
            resets_in=day.ends_in(),
            answers=days[llm.id].answers,
            cached_answers=days[llm.id].cached,
        )
        for llm in llms
    ]
    return sorted(usage, key=lambda used: (-used.estimated_usd, used.name))


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
        llms=await enabled_llms(),
        updated_at=row.limits_updated_at,
        updated_by=await _email(row.limits_updated_by),
        calibration_days=CALIBRATION_DAYS,
    )


@router.get("", response_model=AdminLimits)
async def read_limits() -> AdminLimits:
    return await _to_admin_limits(await get_app_settings())


@router.patch("", response_model=AdminLimits)
async def patch_limits(
    body: AdminLimitsPatch, current_user: RequiredAdmin
) -> AdminLimits:
    changes = body.model_dump(exclude_unset=True)
    if caps := changes.pop("daily_usd_caps", None):
        try:
            await update_daily_caps(caps, updated_by=current_user.id)
        except UnknownLLMsError:
            raise HTTPException(status_code=422, detail="unknown_llm")
    row = await update_limit_settings(changes, updated_by=current_user.id)
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
