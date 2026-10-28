import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.arena.checks import CHUNK_CHARS
from backend.auth.dependencies import RequiredAdmin
from utils.database.actions.llm_analyze import (
    MAX_WINDOWS,
    analysis_for,
    score_comparison,
    update_from_scores,
)
from utils.database.dataset_checks import (
    dataset_check_api_key,
    get_dataset_check,
    update_dataset_check,
)
from utils.database.encrypted import UnreadableSecret
from utils.database.models.dataset_check import (
    CategoryThreshold,
    Criteria,
    DatasetCheck,
    DatasetCheckPublic,
    DatasetCheckUpsert,
    Description,
    LanguageThreshold,
)
from utils.database.settings import get_app_settings
from utils.utils import FormJsonSchema

router = APIRouter(prefix="/dataset-check", tags=["dataset-check"])

# Keys the admin page translates, like the prompt check's.
NO_API_KEY_MESSAGE = "no_api_key"
NO_MODEL_MESSAGE = "no_model"
CALL_FAILED_MESSAGE = "call_failed"


async def _to_public(row: DatasetCheck) -> DatasetCheckPublic:
    return DatasetCheckPublic(
        model=row.model,
        has_api_key=bool(row.api_key),
        description=row.description,
        criteria=row.typed_criteria,
        category_threshold=row.category_threshold,
        language_threshold=row.language_threshold,
        no_api_key=not await dataset_check_api_key(row),
        no_model=not row.model,
        updated_at=row.updated_at.isoformat(),
        updated_by=row.updated_by,
    )


@router.get("", response_model=DatasetCheckPublic)
async def read_dataset_check() -> DatasetCheckPublic:
    return await _to_public(await get_dataset_check())


@router.get("/schema")
async def read_dataset_check_schema():
    return DatasetCheckUpsert.model_json_schema(schema_generator=FormJsonSchema)


@router.put("", response_model=DatasetCheckPublic)
async def put_dataset_check(
    body: DatasetCheckUpsert, current_user: RequiredAdmin
) -> DatasetCheckPublic:
    data = body.model_dump(exclude={"api_key"})
    # A blank key keeps the stored one, as on the prompt check.
    if api_key := (body.api_key or "").strip():
        data["api_key"] = api_key
    row = await update_dataset_check(data, updated_by=current_user.id)
    return await _to_public(row)


@router.delete("/api-key", response_model=DatasetCheckPublic)
async def delete_dataset_check_api_key(
    current_user: RequiredAdmin,
) -> DatasetCheckPublic:
    row = await update_dataset_check({"api_key": None}, updated_by=current_user.id)
    return await _to_public(row)


class DatasetCheckTryBody(BaseModel):
    """A conversation plus, when the admin is trying edits they have not
    saved, the configuration to judge it against. Each field falls back to
    the stored row."""

    text: str = Field(min_length=1, max_length=MAX_WINDOWS * CHUNK_CHARS)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    description: Description | None = None
    criteria: Criteria | None = None
    category_threshold: CategoryThreshold | None = None
    language_threshold: LanguageThreshold | None = None


class DatasetCheckTryResult(BaseModel):
    # Whether the conversation would be published.
    published: bool
    # The exclusion criteria that reached their threshold.
    excluded_by: list[str]
    categories: list[str]
    languages: list[str]
    scores: dict[str, float]
    latency_ms: int
    message: str | None = None
    # What the decision model said when `message` is "call_failed".
    error: str | None = None


def _failed(
    message: str, latency_ms: int = 0, error: str | None = None
) -> DatasetCheckTryResult:
    return DatasetCheckTryResult(
        published=False,
        excluded_by=[],
        categories=[],
        languages=[],
        scores={},
        latency_ms=latency_ms,
        message=message,
        error=error,
    )


@router.post("/try", response_model=DatasetCheckTryResult)
async def try_dataset_check(body: DatasetCheckTryBody) -> DatasetCheckTryResult:
    """Score one pasted conversation the way the publish run would, writing
    nothing."""
    stored = await get_dataset_check()
    check = DatasetCheck(
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
        category_threshold=(
            stored.category_threshold
            if body.category_threshold is None
            else body.category_threshold
        ),
        language_threshold=(
            stored.language_threshold
            if body.language_threshold is None
            else body.language_threshold
        ),
    )
    api_key = await dataset_check_api_key(stored)
    if not check.model:
        return _failed(NO_MODEL_MESSAGE)
    if not api_key or isinstance(api_key, UnreadableSecret):
        return _failed(NO_API_KEY_MESSAGE)

    app_settings = await get_app_settings()
    analysis = analysis_for(
        check, api_key, app_settings.default_locale, app_settings.enabled_locales
    )
    started = time.monotonic()
    try:
        scores = await score_comparison(body.text, analysis)
    except Exception as e:
        return _failed(
            CALL_FAILED_MESSAGE, int((time.monotonic() - started) * 1000), str(e)
        )
    latency_ms = int((time.monotonic() - started) * 1000)

    result = update_from_scores(
        scores,
        check.model,
        analysis.criteria,
        check.category_threshold,
        check.language_threshold,
    )
    return DatasetCheckTryResult(
        published=not result.archived,
        excluded_by=[
            c.key for c in analysis.criteria if scores.get(c.key, 0.0) >= c.threshold
        ],
        categories=result.categories,
        languages=result.languages,
        scores=scores,
        latency_ms=latency_ms,
    )
