import hashlib
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from typing import Any, AsyncGenerator, Awaitable, TypeVar

from fastapi.encoders import jsonable_encoder
from psycopg.errors import QueryCanceled
from pydantic import BaseModel
from sqlalchemy import and_, exists, literal, not_, or_
from sqlalchemy import select as sa_select
from sqlalchemy import tuple_
from sqlalchemy.exc import DBAPIError
from sqlmodel import col, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.config import settings
from backend.statistics.projection import bucket_share, day_share, project
from utils.database.models import Comparison, Turn, UserMessage
from utils.database.models.llms import LLMData
from utils.database.models.utils import escape_like
from utils.database.session import get_activity_session
from utils.storage.redis import REDIS_ADMIN_ACTIVITY_KEY, get_redis_client

from .models import (
    ActivityAnswer,
    ActivityBucket,
    ActivityConversation,
    ActivityConversationRow,
    ActivityConversationsPage,
    ActivityFilterOptions,
    ActivityFilters,
    ActivityLLM,
    ActivityOverview,
    ActivityPoint,
    ActivityPromptCheck,
    ActivityTotals,
    ActivityTurn,
    ConversationFilters,
)

logger = logging.getLogger("languia")

PERIOD_DAYS = {"7d": 7, "30d": 30, "90d": 90, "365d": 365}
TOTAL_CAP = 10_000
FIRST_PROMPT_LENGTH = 280
COMMENT_LENGTH = 200

Cached = TypeVar("Cached", bound=BaseModel)


class QueryTimedOutError(Exception):
    pass


class InvalidCursorError(ValueError):
    pass


@asynccontextmanager
async def _session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with get_activity_session() as session:
            yield session
    except DBAPIError as error:
        if isinstance(error.orig, QueryCanceled):
            raise QueryTimedOutError() from error
        raise


def resolve_range(
    filters: ActivityFilters, now: datetime
) -> tuple[datetime | None, datetime, ActivityBucket]:
    """The period as [start, end), and the bucket size its timeline uses."""
    if filters.start or filters.end:
        start = datetime.combine(filters.start, time.min) if filters.start else None
        end = (
            datetime.combine(filters.end + timedelta(days=1), time.min)
            if filters.end
            else now
        )
    elif filters.period == "24h":
        start, end = now - timedelta(hours=24), now
    elif filters.period == "all":
        start, end = None, now
    else:
        days = PERIOD_DAYS[filters.period]
        start = datetime.combine(now.date() - timedelta(days=days - 1), time.min)
        end = now

    if start is None:
        return None, end, "month"
    span = end - start
    if span <= timedelta(days=2):
        bucket: ActivityBucket = "hour"
    elif span <= timedelta(days=62):
        bucket = "day"
    elif span <= timedelta(days=400):
        bucket = "week"
    else:
        bucket = "month"
    return start, end, bucket


def _truncate(value: datetime, bucket: ActivityBucket) -> datetime:
    if bucket == "hour":
        return value.replace(minute=0, second=0, microsecond=0)
    day = datetime.combine(value.date(), time.min)
    if bucket == "week":
        return day - timedelta(days=day.weekday())
    if bucket == "month":
        return day.replace(day=1)
    return day


def _next_bucket(value: datetime, bucket: ActivityBucket) -> datetime:
    if bucket == "hour":
        return value + timedelta(hours=1)
    if bucket == "day":
        return value + timedelta(days=1)
    if bucket == "week":
        return value + timedelta(days=7)
    return value.replace(
        year=value.year + (value.month == 12), month=value.month % 12 + 1
    )


def _bucket_label(value: datetime, bucket: ActivityBucket) -> str:
    return value.strftime("%Y-%m-%dT%H:00" if bucket == "hour" else "%Y-%m-%d")


def _keeps_archived(filters: ActivityFilters) -> bool:
    # Analysis archives what it flags, so asking for flagged conversations
    # means asking for archived ones.
    flag = getattr(filters, "flag", None)
    return filters.include_archived or flag in ("pii", "spam", "archived")


def _scope(filters: ActivityFilters) -> list[Any]:
    """Conditions on the comparison other than its date."""
    where: list[Any] = []
    if not _keeps_archived(filters):
        where.append(col(Comparison.archived).is_not(True))
    if filters.mode:
        where.append(col(Comparison.mode) == filters.mode)
    if filters.llm_id:
        where.append(
            or_(
                col(Comparison.llm_id_a) == filters.llm_id,
                col(Comparison.llm_id_b) == filters.llm_id,
            )
        )
    if filters.cohort:
        where.append(col(Comparison.cohorts) == filters.cohort)
    return where


def _between(column: Any, start: datetime | None, end: datetime) -> list[Any]:
    return ([column >= start] if start else []) + [column < end]


def _has_error() -> Any:
    # A comparison without an error holds JSON null, not SQL NULL.
    return and_(
        col(Comparison.error).is_not(None),
        func.jsonb_typeof(col(Comparison.error)) != "null",
    )


def _is_vote() -> Any:
    return and_(col(Turn.choice).is_not(None), col(Turn.choice) != "idk")


def _has_comment() -> Any:
    return or_(
        func.coalesce(col(Turn.custom_annotation_a), "") != "",
        func.coalesce(col(Turn.custom_annotation_b), "") != "",
    )


def _has_tag() -> Any:
    return or_(
        func.jsonb_array_length(col(Turn.keyword_annotations_a)) > 0,
        func.jsonb_array_length(col(Turn.keyword_annotations_b)) > 0,
    )


def _cache_key(name: str, filters: BaseModel | None = None) -> str:
    payload = filters.model_dump_json() if filters else ""
    digest = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return REDIS_ADMIN_ACTIVITY_KEY.format(name=name, digest=digest)


def _read_cache(key: str, model: type[Cached]) -> Cached | None:
    try:
        cached = get_redis_client().get(key)
        assert not isinstance(cached, Awaitable)
        if cached is not None:
            return model.model_validate_json(cached)
    except Exception as error:
        logger.warning("Could not read cached admin activity: %s", error)
    return None


def _write_cache(key: str, value: BaseModel) -> None:
    try:
        get_redis_client().setex(
            key, settings.ADMIN_ACTIVITY_CACHE_SECONDS, value.model_dump_json()
        )
    except Exception as error:
        logger.warning("Could not cache admin activity: %s", error)


async def _llms(session: AsyncSession) -> dict[uuid.UUID, ActivityLLM]:
    rows = await session.exec(select(LLMData.id, LLMData.name, LLMData.human_id))
    return {
        id: ActivityLLM(id=id, name=name, human_id=human_id)
        for id, name, human_id in rows.all()
    }


async def get_filter_options(refresh: bool = False) -> ActivityFilterOptions:
    # Imported here: the actions package pulls every data migration with it.
    from utils.database.actions.llm_analyze import Config as AnalyzeConfig

    key = _cache_key("filters")
    if not refresh and (cached := _read_cache(key, ActivityFilterOptions)):
        return cached

    async with _session() as session:
        llms = await _llms(session)
        cohorts = (
            await session.exec(
                select(Comparison.cohorts)
                .where(col(Comparison.cohorts).is_not(None))
                .distinct()
                .order_by(Comparison.cohorts)
            )
        ).all()

    options = ActivityFilterOptions(
        llms=sorted(llms.values(), key=lambda llm: llm.name.lower()),
        cohorts=[cohort for cohort in cohorts if cohort],
        categories=[category.value for category in AnalyzeConfig.TXT360Category],
    )
    _write_cache(key, options)
    return options


async def get_overview(
    filters: ActivityFilters, refresh: bool = False
) -> ActivityOverview:
    key = _cache_key("overview", filters)
    if not refresh and (cached := _read_cache(key, ActivityOverview)):
        return cached

    now = datetime.now()
    start, end, bucket = resolve_range(filters, now)
    scope = _scope(filters)
    comparison_where = scope + _between(col(Comparison.created_at), start, end)
    turn_where = scope + _between(col(Turn.created_at), start, end)

    comparison_bucket = func.date_trunc(bucket, col(Comparison.created_at))
    turn_bucket = func.date_trunc(bucket, col(Turn.created_at))

    async with _session() as session:
        comparison_rows = (
            await session.execute(
                sa_select(
                    comparison_bucket,
                    col(Comparison.mode),
                    func.count(),
                    func.count().filter(col(Comparison.revealed)),
                    func.count().filter(_has_error()),
                )
                .where(*comparison_where)
                .group_by(comparison_bucket, col(Comparison.mode))
            )
        ).all()
        turn_rows = (
            await session.execute(
                sa_select(
                    turn_bucket,
                    col(Turn.choice),
                    func.count(),
                    func.count().filter(_has_comment()),
                    func.count().filter(_has_tag()),
                )
                .select_from(Turn)
                .join(Comparison)
                .where(*turn_where)
                .group_by(turn_bucket, col(Turn.choice))
            )
        ).all()
        voted_conversations = (
            await session.exec(
                select(func.count(func.distinct(col(Turn.comparison_id))))
                .select_from(Turn)
                .join(Comparison)
                .where(*comparison_where, _is_vote())
            )
        ).one()
        # A range that ends now has its last bucket still filling up.
        ongoing = end == now
        share_of_today = await day_share(session, now) if ongoing else 0.0

    points: dict[datetime, dict[str, int]] = {}

    def point(at: datetime) -> dict[str, int]:
        return points.setdefault(at, {"conversations": 0, "prompts": 0, "votes": 0})

    modes: dict[str, int] = {}
    revealed = errored = 0
    for at, mode, count, revealed_count, errored_count in comparison_rows:
        point(at)["conversations"] += count
        modes[mode] = modes.get(mode, 0) + count
        revealed += revealed_count
        errored += errored_count

    choices: dict[str, int] = {}
    comments = tagged = 0
    for at, choice, count, comment_count, tagged_count in turn_rows:
        point(at)["prompts"] += count
        if choice is not None and choice != "idk":
            point(at)["votes"] += count
        choices[choice or "none"] = choices.get(choice or "none", 0) + count
        comments += comment_count
        tagged += tagged_count

    first = _truncate(start, bucket) if start else min(points, default=None)
    activity: list[ActivityPoint] = []
    if first is not None:
        cursor, last = first, _truncate(end - timedelta(microseconds=1), bucket)
        while cursor <= last:
            counts = points.get(cursor, {})
            activity.append(
                ActivityPoint(
                    date=_bucket_label(cursor, bucket),
                    conversations=counts.get("conversations", 0),
                    prompts=counts.get("prompts", 0),
                    votes=counts.get("votes", 0),
                )
            )
            cursor = _next_bucket(cursor, bucket)
        if ongoing and activity:
            last_start = max(last, start) if start else last
            share = bucket_share(
                last_start, _next_bucket(last, bucket), now, bucket, share_of_today
            )
            current = activity[-1]
            current.partial = True
            current.projected_conversations = project(current.conversations, share)
            current.projected_prompts = project(current.prompts, share)
            current.projected_votes = project(current.votes, share)

    overview = ActivityOverview(
        range_start=start,
        range_end=end,
        bucket=bucket,
        totals=ActivityTotals(
            conversations=sum(modes.values()),
            prompts=sum(choices.values()),
            votes=sum(
                count
                for choice, count in choices.items()
                if choice not in ("none", "idk")
            ),
            idk=choices.get("idk", 0),
            comments=comments,
            tagged=tagged,
            voted_conversations=voted_conversations,
            revealed_conversations=revealed,
            errored_conversations=errored,
        ),
        activity=activity,
        choices=choices,
        modes=modes,
        computed_at=now,
    )
    _write_cache(key, overview)
    return overview


def encode_cursor(created_at: datetime, comparison_id: uuid.UUID) -> str:
    return f"{created_at.isoformat()}_{comparison_id}"


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    try:
        created_at, comparison_id = cursor.rsplit("_", 1)
        return datetime.fromisoformat(created_at), uuid.UUID(comparison_id)
    except ValueError as error:
        raise InvalidCursorError(cursor) from error


def _turn_exists(*conditions: Any) -> Any:
    return exists(
        select(literal(1)).where(
            col(Turn.comparison_id) == col(Comparison.id), *conditions
        )
    )


def _conversation_conditions(filters: ConversationFilters) -> list[Any]:
    start, end, _ = resolve_range(filters, datetime.now())
    where = _scope(filters) + _between(col(Comparison.created_at), start, end)

    if filters.choice:
        where.append(_turn_exists(col(Turn.choice) == filters.choice))
    if filters.has_vote is not None:
        voted = _turn_exists(_is_vote())
        where.append(voted if filters.has_vote else not_(voted))
    if filters.has_comment is not None:
        commented = _turn_exists(_has_comment())
        where.append(commented if filters.has_comment else not_(commented))
    if filters.revealed is not None:
        where.append(col(Comparison.revealed).is_(filters.revealed))
    if filters.category:
        where.append(col(Comparison.categories).contains([filters.category]))
    if filters.flag == "pii":
        where.append(col(Comparison.contains_pii).is_(True))
    elif filters.flag == "spam":
        where.append(col(Comparison.contains_spam).is_(True))
    elif filters.flag == "error":
        where.append(_has_error())
    elif filters.flag == "archived":
        where.append(col(Comparison.archived).is_(True))
    elif filters.flag == "not_analyzed":
        where.append(col(Comparison.llm_analyzed).is_not(True))
    if filters.search:
        where.append(
            exists(
                select(literal(1))
                .select_from(Turn)
                .join(UserMessage, col(UserMessage.turn_id) == col(Turn.id))
                .where(
                    col(Turn.comparison_id) == col(Comparison.id),
                    col(UserMessage.content).ilike(
                        f"%{escape_like(filters.search)}%", escape="\\"
                    ),
                )
            )
        )
    return where


async def list_conversations(
    filters: ConversationFilters,
) -> ActivityConversationsPage:
    where = _conversation_conditions(filters)
    page_where = list(where)
    if filters.cursor:
        created_at, comparison_id = decode_cursor(filters.cursor)
        page_where.append(
            tuple_(col(Comparison.created_at), col(Comparison.id))
            < tuple_(literal(created_at), literal(comparison_id))
        )

    async with _session() as session:
        comparisons = (
            await session.execute(
                sa_select(
                    col(Comparison.id),
                    col(Comparison.created_at),
                    col(Comparison.mode),
                    col(Comparison.cohorts),
                    col(Comparison.llm_id_a),
                    col(Comparison.llm_id_b),
                    col(Comparison.revealed),
                    col(Comparison.categories),
                    col(Comparison.llm_analyzed),
                    col(Comparison.contains_pii),
                    col(Comparison.contains_spam),
                    col(Comparison.archived),
                    _has_error(),
                )
                .where(*page_where)
                .order_by(col(Comparison.created_at).desc(), col(Comparison.id).desc())
                .limit(filters.limit + 1)
            )
        ).all()
        has_more = len(comparisons) > filters.limit
        comparisons = comparisons[: filters.limit]

        turns = (
            (
                await session.execute(
                    sa_select(
                        col(Turn.comparison_id),
                        col(Turn.choice),
                        col(Turn.keyword_annotations_a),
                        col(Turn.keyword_annotations_b),
                        _has_comment(),
                        func.left(col(UserMessage.content), FIRST_PROMPT_LENGTH),
                        func.left(
                            func.coalesce(
                                func.nullif(col(Turn.custom_annotation_a), ""),
                                func.nullif(col(Turn.custom_annotation_b), ""),
                            ),
                            COMMENT_LENGTH,
                        ),
                    )
                    .outerjoin(UserMessage, col(UserMessage.turn_id) == col(Turn.id))
                    .where(col(Turn.comparison_id).in_([row[0] for row in comparisons]))
                    .order_by(col(Turn.created_at))
                )
            ).all()
            if comparisons
            else []
        )

        total: int | None = None
        if not filters.cursor:
            total = (
                await session.exec(
                    select(func.count()).select_from(
                        select(Comparison.id)
                        .where(*where)
                        .limit(TOTAL_CAP + 1)
                        .subquery()
                    )
                )
            ).one()

        llms = await _llms(session)

    by_comparison: dict[uuid.UUID, list[Any]] = {}
    for turn in turns:
        by_comparison.setdefault(turn[0], []).append(turn)

    items = []
    for (
        id,
        created_at,
        mode,
        cohorts,
        llm_id_a,
        llm_id_b,
        revealed,
        categories,
        llm_analyzed,
        contains_pii,
        contains_spam,
        archived,
        has_error,
    ) in comparisons:
        comparison_turns = by_comparison.get(id, [])
        tags_a = dict.fromkeys(tag for turn in comparison_turns for tag in turn[2])
        tags_b = dict.fromkeys(tag for turn in comparison_turns for tag in turn[3])
        comments = [turn[6] for turn in comparison_turns if turn[6]]
        items.append(
            ActivityConversationRow(
                id=id,
                created_at=created_at,
                mode=mode,
                cohorts=cohorts,
                model_a=llms.get(llm_id_a),
                model_b=llms.get(llm_id_b),
                first_prompt=(comparison_turns[0][5] or "") if comparison_turns else "",
                turns=len(comparison_turns),
                choices=[turn[1] for turn in comparison_turns],
                tags_a=list(tags_a),
                tags_b=list(tags_b),
                has_comment=any(turn[4] for turn in comparison_turns),
                comment=comments[0] if comments else None,
                revealed=revealed,
                categories=categories or [],
                llm_analyzed=bool(llm_analyzed),
                contains_pii=bool(contains_pii),
                contains_spam=bool(contains_spam),
                archived=bool(archived),
                has_error=bool(has_error),
            )
        )

    last = comparisons[-1] if comparisons else None
    return ActivityConversationsPage(
        items=items,
        next_cursor=encode_cursor(last[1], last[0]) if has_more and last else None,
        total=min(total, TOTAL_CAP) if total is not None else None,
        total_capped=total is not None and total > TOTAL_CAP,
    )


def _answer(message: Any) -> ActivityAnswer | None:
    if message is None:
        return None
    duration = (
        int((message.responded_at - message.created_at).total_seconds() * 1000)
        if message.responded_at and message.created_at
        else None
    )
    return ActivityAnswer(
        content=message.content or "",
        reasoning_content=message.reasoning_content,
        tokens=message.tokens,
        duration_ms=duration,
    )


async def get_conversation(comparison_id: uuid.UUID) -> ActivityConversation | None:
    async with _session() as session:
        comparison = await session.get(Comparison, comparison_id)
        if comparison is None:
            return None
        llms = await _llms(session)

        turns = []
        for turn in comparison.turns:
            check = turn.prompt_check_result
            turns.append(
                ActivityTurn(
                    id=turn.id,
                    created_at=turn.created_at,
                    prompt=turn.user_msg.content if turn.user_msg else "",
                    web_search_results=(
                        jsonable_encoder(turn.user_msg.web_search_results)
                        if turn.user_msg and turn.user_msg.web_search_results
                        else None
                    ),
                    answer_a=_answer(turn.llm_msg_a),
                    answer_b=_answer(turn.llm_msg_b),
                    choice=turn.choice,
                    voted_at=turn.voted_at,
                    tags_a=turn.keyword_annotations_a or [],
                    tags_b=turn.keyword_annotations_b or [],
                    comment_a=turn.custom_annotation_a,
                    comment_b=turn.custom_annotation_b,
                    prompt_check=(
                        ActivityPromptCheck(
                            decision=check.decision,
                            model=check.model,
                            triggered=check.triggered,
                            user_proceeded=check.user_proceeded,
                        )
                        if check
                        else None
                    ),
                )
            )

        return ActivityConversation(
            id=comparison.id,
            created_at=comparison.created_at,
            mode=comparison.mode,
            cohorts=comparison.cohorts,
            revealed=comparison.revealed,
            revealed_at=comparison.revealed_at,
            model_a=llms.get(comparison.llm_id_a),
            model_b=llms.get(comparison.llm_id_b),
            system_msg_a=comparison.system_msg_a,
            system_msg_b=comparison.system_msg_b,
            llm_analyzed=bool(comparison.llm_analyzed),
            short_summary=comparison.short_summary,
            keywords=comparison.keywords or [],
            categories=comparison.categories or [],
            languages=comparison.languages or [],
            contains_pii=bool(comparison.contains_pii),
            contains_spam=bool(comparison.contains_spam),
            archived=bool(comparison.archived),
            archived_reason=comparison.archived_reason,
            error=comparison.error,
            turns=turns,
        )
