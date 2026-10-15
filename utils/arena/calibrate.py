"""
What people really spend of the model allowances, replayed from the stored
comparisons through the charging rule the arena applies today, to set the
allowances from it. Read-only. The CLI prints the whole replay; the admin's
"Calibrer" button reads a bounded sample and gets values to propose.

Each turn costs what both models were sent (system prompt, every turn so far
with its web search results, that side's earlier answers) and what they
wrote, priced at today's model prices and threshold. What the database
cannot tell is left out: a failed attempt that a retry or a stand-in
replaced, and a prompt refused before it reached the models.
"""

import logging
import math
import uuid
from collections import defaultdict
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, AsyncGenerator, Callable, Sequence

import numpy as np
from linkup import LinkupSearchTextResult
from psycopg.errors import QueryCanceled
from sqlalchemy import Row, case, func, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import aliased
from sqlmodel import col
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.activity.services import QueryTimedOutError
from backend.arena.limits import (
    DAY_ZONE,
    MICRO_USD,
    POOL_SETTINGS,
    POOLS,
    WHOLE_SETTINGS,
    WINDOW_SECONDS,
    Call,
    LimitSetting,
    Pool,
    Priced,
    counted,
    day_cost,
    is_expensive,
    limit,
    load_settings,
    setting,
    turn_cost,
)
from backend.arena.models import (
    DailyCapProposal,
    LimitProposal,
    LimitsCalibration,
    LLMPrice,
    PriceCheck,
    PriceIssue,
)
from backend.arena.web_search import merge_web_search_with_content
from backend.config import settings
from backend.utils.user import ip_bucket
from utils.database.models import (
    Comparison,
    LLMMessage,
    PromptSuggestion,
    Turn,
    UserMessage,
)
from utils.database.models.llms import LLMData
from utils.database.session import get_activity_session, get_session

logger = logging.getLogger("comparia.arena")

PERCENTILES = (50, 90, 95, 99)

# What the admin's button reads: a week, the latest comparisons only, on the
# activity panel's engine and its statement timeout, so it answers in seconds
# and cannot crowd the arena out of Postgres.
CALIBRATION_DAYS = 7
CALIBRATION_MAX_COMPARISONS = 30_000

# An output price no model sold per million tokens comes near, in dollars.
# The priciest of the seed is 26.
VERY_HIGH_PRICE_OUT = 100

# A session allowance that 99 in 100 people's two hours stay under.
SESSION_PERCENTILE = 99
# A network allowance that lets a class through, each pupil spending what 95
# in 100 people do. Pix sends whole classes from one school IP.
CLASS_SIZE = 35
CLASS_PERCENTILE = 95
# Below this many two-hour windows, or answers, a proposal is said to be
# unreliable. The 99th percentile of fewer than 100 values is the largest of
# them, so a single heavy user would set the allowance for everyone.
MIN_SAMPLE = 100
# A daily cap per expensive model: what 95 in 100 of its days stayed under,
# with half again as much room, so an ordinary busy day never meets it and
# only a day far out of the ordinary does.
DAY_PERCENTILE = 95
DAY_MARGIN = 1.5


@dataclass
class Spend:
    """When each turn was sent, and what it cost of each pool."""

    turns: list[tuple[datetime, dict[Pool, int]]] = field(default_factory=list)

    def add(self, at: datetime, cost: dict[Pool, int]) -> None:
        self.turns.append((at, cost))

    def windows(self, pool: Pool) -> list[int]:
        """What the counter would have held in each window: a window opens
        with the first turn that charges the pool and closes two hours later,
        however many turns follow."""
        totals: list[int] = []
        opened: datetime | None = None
        for at, cost in sorted(self.turns, key=lambda turn: turn[0]):
            if pool not in cost:
                continue
            if opened is None or at - opened >= timedelta(seconds=WINDOW_SECONDS):
                totals.append(0)
                opened = at
            totals[-1] += cost[pool]
        return totals

    def hours(self, pool: Pool) -> list[int]:
        """What each clock hour spent of the pool."""
        totals: dict[datetime, int] = defaultdict(int)
        for at, cost in self.turns:
            if pool in cost:
                totals[at.replace(minute=0, second=0, microsecond=0)] += cost[pool]
        return list(totals.values())


@dataclass(frozen=True)
class Prices:
    """A model's prices, in US dollars per million tokens."""

    price_in: float
    price_out: float


# A model the database no longer knows costs nothing.
UNPRICED = Prices(0.0, 0.0)


@dataclass
class Side:
    """One side of a conversation: its model's prices, and what it is sent
    before the next prompt."""

    llm: Priced
    transcript: int
    llm_id: uuid.UUID


@dataclass
class Replay:
    conversations: list[dict[Pool, int]] = field(default_factory=list)
    people: dict[str, Spend] = field(default_factory=lambda: defaultdict(Spend))
    networks: dict[str, Spend] = field(default_factory=lambda: defaultdict(Spend))
    unknown_people: int = 0
    turns: int = 0
    # What each turn cost of each pool it charged.
    turn_costs: dict[Pool, list[int]] = field(default_factory=lambda: defaultdict(list))
    answers: int = 0
    cached: int = 0
    # What each answer wrote, its reasoning included.
    written: list[int] = field(default_factory=list)
    suggested_answers: int = 0
    suggested_cached: int = 0
    # What each model cost on each Paris calendar day, in millionths of a
    # dollar, and every day a turn was sent on.
    model_days: dict[uuid.UUID, dict[date, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    days: set[date] = field(default_factory=set)


def _prompt_chars(row: Row[Any]) -> int:
    # A JSON null in the column is not an SQL NULL, so the text can come
    # with no results to merge.
    if not row.web_search:
        return int(row.prompt_chars)
    results = [LinkupSearchTextResult.model_validate(r) for r in row.web_search]
    return len(merge_web_search_with_content(row.searched, results))


def replay(rows: Sequence[Row[Any]], prices: dict[uuid.UUID, Prices]) -> Replay:
    """Rows are turns, each comparison's in the order they were sent."""
    result = Replay()
    sides: dict[str, Side] = {}
    current: uuid.UUID | None = None
    spent: dict[Pool, int] = {}

    for row in rows:
        if row.comparison_id != current:
            if current is not None:
                result.conversations.append(spent)
            current, spent = row.comparison_id, {}
            sides = {
                "a": Side(
                    prices.get(row.llm_id_a, UNPRICED), row.system_a, row.llm_id_a
                ),
                "b": Side(
                    prices.get(row.llm_id_b, UNPRICED), row.system_b, row.llm_id_b
                ),
            }
            # A signed-in person's comparisons keep no session, only the
            # account.
            person = (
                f"s:{row.anonymous_user_hash}"
                if row.anonymous_user_hash
                else f"u:{row.user_id}" if row.user_id else None
            )
            if person is None:
                result.unknown_people += 1
            network = ip_bucket(row.ip)
            first = True

        prompt = _prompt_chars(row)
        calls = []
        for pos, side in sides.items():
            content = getattr(row, f"content_{pos}")
            reasoning = getattr(row, f"reasoning_{pos}")
            # None when the side has no answer, such as a failed turn.
            cached = getattr(row, f"cached_{pos}")
            if cached is not None:
                result.answers += 1
                result.written.append(content + reasoning)
                result.cached += cached
                if first and row.suggested:
                    result.suggested_answers += 1
                    result.suggested_cached += cached
            call = Call.of(side.llm, side.transcript + prompt, content + reasoning)
            call.cached = bool(cached)
            call.llm_id = side.llm_id
            calls.append(call)
            # Only the answer goes back to the model next turn, not its
            # reasoning.
            side.transcript += prompt + content

        # The stored times are the host's local time, as AutoDatetime keeps
        # them.
        day = row.created_at.astimezone(DAY_ZONE).date()
        result.days.add(day)
        for llm_id, spent_today in day_cost(calls).items():
            result.model_days[llm_id][day] += spent_today.get("usd", 0)

        cost = turn_cost(calls)
        for pool, chars in cost.items():
            spent[pool] = spent.get(pool, 0) + chars
            result.turn_costs[pool].append(chars)
        if person:
            result.people[person].add(row.created_at, cost)
        result.networks[network].add(row.created_at, cost)
        result.turns += 1
        first = False

    if current is not None:
        result.conversations.append(spent)
    return result


async def _read(
    days: int,
    max_comparisons: int | None = None,
    session_factory: Callable[
        [], AbstractAsyncContextManager[AsyncSession]
    ] = get_session,
) -> tuple[Sequence[Row[Any]], dict[uuid.UUID, Prices]]:
    """The turns of the comparisons started in the last `days`, the latest
    `max_comparisons` of them when set, and each model's prices."""
    since = datetime.now() - timedelta(days=days)
    answer_a, answer_b = aliased(LLMMessage), aliased(LLMMessage)
    has_search = col(UserMessage.web_search_results).is_not(None)
    suggestions = select(func.btrim(PromptSuggestion.text))

    def chars(column: Any) -> Any:
        return func.coalesce(func.char_length(column), 0)

    query = (
        select(
            col(Comparison.id).label("comparison_id"),
            col(Comparison.ip),
            col(Comparison.anonymous_user_hash),
            col(Comparison.user_id),
            col(Comparison.llm_id_a),
            col(Comparison.llm_id_b),
            chars(Comparison.system_msg_a).label("system_a"),
            chars(Comparison.system_msg_b).label("system_b"),
            col(Turn.created_at),
            chars(UserMessage.content).label("prompt_chars"),
            # The text only when it has search results to merge with.
            case((has_search, UserMessage.content)).label("searched"),
            col(UserMessage.web_search_results).label("web_search"),
            func.btrim(UserMessage.content).in_(suggestions).label("suggested"),
            chars(answer_a.content).label("content_a"),
            chars(answer_a.reasoning_content).label("reasoning_a"),
            col(answer_a.is_cached).label("cached_a"),
            chars(answer_b.content).label("content_b"),
            chars(answer_b.reasoning_content).label("reasoning_b"),
            col(answer_b.is_cached).label("cached_b"),
        )
        .join(Turn, col(Turn.comparison_id) == Comparison.id)
        .join(UserMessage, col(UserMessage.turn_id) == Turn.id)
        .outerjoin(answer_a, col(answer_a.id) == Turn.llm_msg_a_id)
        .outerjoin(answer_b, col(answer_b.id) == Turn.llm_msg_b_id)
        .where(col(Comparison.created_at) >= since)
        .order_by(col(Comparison.id), col(Turn.created_at))
    )
    if max_comparisons is not None:
        latest = (
            select(col(Comparison.id))
            .where(col(Comparison.created_at) >= since)
            .order_by(col(Comparison.created_at).desc())
            .limit(max_comparisons)
        )
        query = query.where(col(Comparison.id).in_(latest))
    async with session_factory() as session:
        rows = (await session.execute(query)).all()
        prices = {
            llm_id: Prices(price_in, price_out)
            for llm_id, price_in, price_out in (
                await session.execute(
                    select(
                        col(LLMData.id), col(LLMData.price_in), col(LLMData.price_out)
                    )
                )
            ).all()
        }
    return rows, prices


def round_up(value: float) -> int:
    """Up to two significant digits, so a proposal reads as a round number."""
    if value <= 0:
        return 0
    step = 10 ** max(0, math.floor(math.log10(value)) - 1)
    return int(math.ceil(value / step) * step)


# Cents in a dollar, the smallest step the admin edits dollars in.
CENTS = 100


def in_setting_unit(pool: Pool, value: float) -> float:
    """A counter's value, rounded up to two significant digits, in the unit
    its setting is in: characters, or dollars to the cent."""
    if pool == "all":
        return round_up(value)
    return round_up(value * CENTS / MICRO_USD) / CENTS


def smallest(pool: Pool) -> float:
    """The smallest value a setting of this pool may take."""
    return 1 if pool == "all" else 1 / CENTS


def _percentile(values: list[int], percentile: int) -> float:
    return float(np.percentile(values, percentile))


def propose(result: Replay) -> list[LimitProposal]:
    """
    The limits this replay suggests: per session, what 99 in 100 people's
    two hours stay under; per network, room for a class of 35 that each spend
    what 95 in 100 people do, never below the session one; the expected
    answer, the median answer. A pool nobody spent proposes nothing.
    """
    proposals: list[LimitProposal] = []
    for pool in POOLS:
        people = [w for spend in result.people.values() for w in spend.windows(pool)]
        if not people:
            continue
        per_session = max(
            smallest(pool),
            in_setting_unit(pool, _percentile(people, SESSION_PERCENTILE)),
        )
        typical_turn = _percentile(result.turn_costs[pool], 50)
        if pool == "expensive":
            typical_turn /= MICRO_USD
        proposals.append(
            LimitProposal(
                name=POOL_SETTINGS[(pool, "session")],
                value=per_session,
                sample=len(people),
                percentile=SESSION_PERCENTILE,
                messages=int(per_session // typical_turn) if typical_turn else None,
                few=len(people) < MIN_SAMPLE,
            )
        )

        networks = [
            w for spend in result.networks.values() for w in spend.windows(pool)
        ]
        per_network = max(
            per_session,
            in_setting_unit(pool, CLASS_SIZE * _percentile(people, CLASS_PERCENTILE)),
        )
        # The networks' windows are compared in the counters' unit.
        over = round(per_network * MICRO_USD) if pool == "expensive" else per_network
        proposals.append(
            LimitProposal(
                name=POOL_SETTINGS[(pool, "network")],
                value=per_network,
                sample=len(networks),
                percentile=CLASS_PERCENTILE,
                class_size=CLASS_SIZE,
                over_share=(
                    sum(w > over for w in networks) / len(networks)
                    if networks
                    else None
                ),
                # Read from the people's windows, like the session one.
                few=len(people) < MIN_SAMPLE,
            )
        )

    if result.written:
        proposals.append(
            LimitProposal(
                name="expected_answer_chars",
                value=int(_percentile(result.written, 50)),
                sample=len(result.written),
                percentile=50,
                few=len(result.written) < MIN_SAMPLE,
            )
        )
    return proposals


def complete_days(result: Replay, today: date) -> list[date]:
    """The days the replay saw whole: not today, which is not over, nor the
    first one, which the sample may start in the middle of."""
    return sorted(day for day in result.days if day != today)[1:]


def propose_daily_caps(
    result: Replay, llms: Sequence[LLMPrice], today: date
) -> list[DailyCapProposal]:
    """
    A daily cap for each enabled expensive model: what 95 in 100 of its
    whole days cost, days it was not drawn counting as nothing, with half
    again as much room, in dollars rounded up to two digits and the cent.
    A model that cost nothing on any of them gets no proposal.
    """
    days = complete_days(result, today)
    proposals: list[DailyCapProposal] = []
    for llm in llms:
        if not is_expensive(llm):
            continue
        spent = [result.model_days.get(llm.id, {}).get(day, 0) for day in days]
        if not any(spent):
            continue
        proposals.append(
            DailyCapProposal(
                llm_id=llm.id,
                value=max(
                    smallest("expensive"),
                    in_setting_unit(
                        "expensive",
                        DAY_MARGIN * _percentile(spent, DAY_PERCENTILE),
                    ),
                ),
                days=len(days),
                percentile=DAY_PERCENTILE,
                highest=max(spent) / MICRO_USD,
            )
        )
    return proposals


def paris_today() -> date:
    return datetime.now(DAY_ZONE).date()


async def enabled_llms(
    session_factory: Callable[
        [], AbstractAsyncContextManager[AsyncSession]
    ] = get_session,
) -> list[LLMPrice]:
    """The enabled models and their prices, the priciest first."""
    query = (
        select(
            col(LLMData.id),
            col(LLMData.name),
            col(LLMData.price_in),
            col(LLMData.price_out),
        )
        .where(col(LLMData.status) == "enabled")
        .order_by(col(LLMData.price_out).desc(), col(LLMData.name))
    )
    async with session_factory() as session:
        rows = (await session.execute(query)).all()
    return [
        LLMPrice(id=id, name=name, price_in=price_in, price_out=price_out)
        for id, name, price_in, price_out in rows
    ]


def price_issue(llm: Priced) -> PriceIssue | None:
    """What looks wrong with a model's prices, if anything."""
    if llm.price_out <= 0:
        return "free"
    if llm.price_in <= 0:
        return "free_input"
    if llm.price_out < llm.price_in:
        return "output_below_input"
    if llm.price_out > VERY_HIGH_PRICE_OUT:
        return "very_high"
    return None


def check_prices(llms: Sequence[LLMPrice]) -> list[PriceCheck]:
    return [
        PriceCheck(**llm.model_dump(), issue=issue)
        for llm in llms
        if (issue := price_issue(llm))
    ]


@asynccontextmanager
async def _bounded_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with get_activity_session() as session:
            yield session
    except DBAPIError as error:
        if isinstance(error.orig, QueryCanceled):
            raise QueryTimedOutError() from error
        raise


async def calibrate(
    days: int = CALIBRATION_DAYS, max_comparisons: int = CALIBRATION_MAX_COMPARISONS
) -> LimitsCalibration:
    """
    Replay a bounded sample of the latest comparisons and propose limits from
    it, for the admin. Read-only.

    Raises:
        QueryTimedOutError: the read ran past the statement timeout
    """
    # Whether a model is expensive reads the threshold in force.
    await load_settings()
    rows, prices = await _read(days, max_comparisons, _bounded_session)
    result = replay(rows, prices)
    llms = await enabled_llms(_bounded_session)
    return LimitsCalibration(
        days=days,
        comparisons=len(result.conversations),
        turns=result.turns,
        capped=len(result.conversations) >= max_comparisons,
        proposals=propose(result),
        daily_caps=propose_daily_caps(result, llms, paris_today()),
        price_checks=check_prices(llms),
    )


def _line(
    name: str, values: list[int], limit: int | None = None, pool: Pool = "all"
) -> str:
    if not values:
        return f"{name}: nothing"
    shown = ", ".join(
        f"p{p} {counted(pool, v)}"
        for p, v in zip(PERCENTILES, np.percentile(values, PERCENTILES))
    )
    line = f"{name}: {shown}, max {counted(pool, max(values))} ({len(values):,})"
    if limit is not None:
        over = sum(value > limit for value in values) / len(values)
        line += f", limit {counted(pool, limit)}, {over:.1%} over"
    return line


async def limits_calibrate(*, days: int = 30) -> None:
    """
    Replay the comparisons of the last days through the charging rule and
    print what the allowances would have counted: per person and per network
    in each two-hour window, per network in each clock hour, per conversation,
    how long answers run, and the share of answers served from the cache.
    Read-only.

    Args:
        days: How far back to read
    """
    if not settings.COMPARIA_DB_URI:
        logger.error("COMPARIA_DB_URI is not set, nothing to read")
        raise SystemExit(1)

    # The limits in force, an admin's or the defaults: the threshold decides
    # which models are expensive.
    await load_settings()
    rows, prices = await _read(days)
    result = replay(rows, prices)
    logger.info(
        f"{len(result.conversations):,} comparisons and {result.turns:,} turns "
        f"over {days} days; {len(result.people):,} people, "
        f"{len(result.networks):,} networks, {result.unknown_people:,} "
        f"comparisons with no person to count them against"
    )

    for pool in POOLS:
        people = [w for spend in result.people.values() for w in spend.windows(pool)]
        networks = [
            w for spend in result.networks.values() for w in spend.windows(pool)
        ]
        hours = [h for spend in result.networks.values() for h in spend.hours(pool)]
        conversations = [spent[pool] for spent in result.conversations if pool in spent]
        logger.info(
            _line(
                f"{pool}, per person and window",
                people,
                limit(pool, "session"),
                pool,
            )
        )
        logger.info(
            _line(
                f"{pool}, per network and window",
                networks,
                limit(pool, "network"),
                pool,
            )
        )
        logger.info(_line(f"{pool}, per network and hour", hours, pool=pool))
        logger.info(_line(f"{pool}, per conversation", conversations, pool=pool))

    # The median sets RATELIMIT_EXPECTED_ANSWER_CHARS.
    logger.info(_line("Characters written per answer", result.written))

    def share(part: int, whole: int) -> str:
        return f"{part / whole:.1%} of {whole:,}" if whole else "none"

    logger.info(
        f"Cached answers: {share(result.cached, result.answers)}; on first "
        f"turns of a suggested prompt: "
        f"{share(result.suggested_cached, result.suggested_answers)}"
    )

    def shown(name: LimitSetting, value: float) -> str:
        return f"{int(value):,}" if name in WHOLE_SETTINGS else f"${value:,.2f}"

    for proposal in propose(result):
        logger.info(
            f"Proposed {proposal.name}: {shown(proposal.name, proposal.value)} "
            f"(now {shown(proposal.name, setting(proposal.name))})"
            + (
                f", from only {proposal.sample:,}: too few to trust"
                if proposal.few
                else ""
            )
        )
    llms = await enabled_llms()
    names = {llm.id: llm.name for llm in llms}
    for cap in propose_daily_caps(result, llms, paris_today()):
        logger.info(
            f"Proposed daily cap of {names[cap.llm_id]}: ${cap.value:,.2f} "
            f"(p{cap.percentile} of {cap.days} days times {DAY_MARGIN}, "
            f"highest ${cap.highest:,.2f})"
        )
    for check in check_prices(llms):
        logger.warning(
            f"Check the prices of {check.name} ({check.id}): {check.issue}, "
            f"{check.price_in} in and {check.price_out} out per million tokens"
        )
