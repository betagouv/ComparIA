import logging
import time
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from backend.arena.checks import (
    list_decision_models,
    read_cached_scores,
    score_prompt,
    verdict,
    write_cached_scores,
)
from backend.auth.dependencies import RequiredAdmin
from backend.config import BLIND_MODE_INPUT_CHAR_LEN_LIMIT, settings
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
from utils.utils import FormJsonSchema

logger = logging.getLogger("languia")

router = APIRouter(prefix="/prompt-check", tags=["prompt-check"])


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


@router.get("", response_model=PromptCheckStatus)
async def read_prompt_check() -> PromptCheckStatus:
    return _to_prompt_check_status(await get_prompt_check())


@router.get("/schema")
async def read_prompt_check_schema():
    return PromptCheckUpsert.model_json_schema(schema_generator=FormJsonSchema)


@router.put("", response_model=PromptCheckStatus)
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


@router.delete("/api-key", response_model=PromptCheckStatus)
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


@router.post("/try", response_model=PromptCheckTryResult)
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


@router.get("/models", response_model=list[PromptCheckModel])
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


@router.get("/stats", response_model=PromptCheckStats)
async def read_prompt_check_stats(
    period: Literal["all", "7d", "30d", "90d", "365d"] = Query(default="all"),
) -> PromptCheckStats:
    """Historical total and period-filtered activity.

    `by_criterion` counts the turns each criterion triggered on, so one turn can
    count in several. The timeline uses daily, weekly or monthly buckets based
    on the selected period.
    """
    return PromptCheckStats(**await get_prompt_check_stats(period))
