"""
What people really spend of the model allowances, replayed from the stored
comparisons through the charging rule the arena applies today, to set the
allowances from it. Read-only.

Each turn costs what both models were sent (system prompt, every turn so far
with its web search results, that side's earlier answers) and what they
wrote, weighted by today's cost weights. What the database cannot tell is
left out: a failed attempt that a retry or a stand-in replaced, and a prompt
refused before it reached the models.
"""

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Sequence

import numpy as np
from linkup import LinkupSearchTextResult
from sqlalchemy import Row, case, func, select
from sqlalchemy.orm import aliased
from sqlmodel import col

from backend.arena.limits import POOLS, WINDOW_SECONDS, Call, Pool, turn_cost
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
from utils.database.session import get_session

logger = logging.getLogger("comparia.arena")

PERCENTILES = (50, 90, 95, 99)


@dataclass
class Spend:
    """When each turn was sent, and what it cost of each pool."""

    turns: list[tuple[datetime, dict[Pool, int]]] = field(default_factory=list)

    def add(self, at: datetime, cost: dict[Pool, int]) -> None:
        self.turns.append((at, cost))

    def windows(self, pool: Pool) -> list[int]:
        """What the counter would have held in each window: every turn that
        charges the pool keeps it open two more hours."""
        totals: list[int] = []
        last: datetime | None = None
        for at, cost in sorted(self.turns, key=lambda turn: turn[0]):
            if pool not in cost:
                continue
            if last is None or at - last >= timedelta(seconds=WINDOW_SECONDS):
                totals.append(0)
            totals[-1] += cost[pool]
            last = at
        return totals

    def hours(self, pool: Pool) -> list[int]:
        """What each clock hour spent of the pool."""
        totals: dict[datetime, int] = defaultdict(int)
        for at, cost in self.turns:
            if pool in cost:
                totals[at.replace(minute=0, second=0, microsecond=0)] += cost[pool]
        return list(totals.values())


@dataclass
class Side:
    """One side of a conversation: its cost weight, and what it is sent
    before the next prompt."""

    weight: float
    transcript: int


@dataclass
class Replay:
    conversations: list[dict[Pool, int]] = field(default_factory=list)
    people: dict[str, Spend] = field(default_factory=lambda: defaultdict(Spend))
    networks: dict[str, Spend] = field(default_factory=lambda: defaultdict(Spend))
    unknown_people: int = 0
    turns: int = 0
    answers: int = 0
    cached: int = 0
    suggested_answers: int = 0
    suggested_cached: int = 0


def _prompt_chars(row: Row[Any]) -> int:
    if row.searched is None:
        return int(row.prompt_chars)
    results = [LinkupSearchTextResult.model_validate(r) for r in row.web_search]
    return len(merge_web_search_with_content(row.searched, results))


def replay(rows: Sequence[Row[Any]], weights: dict[uuid.UUID, float]) -> Replay:
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
                "a": Side(weights.get(row.llm_id_a, 1.0), row.system_a),
                "b": Side(weights.get(row.llm_id_b, 1.0), row.system_b),
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
                result.cached += cached
                if first and row.suggested:
                    result.suggested_answers += 1
                    result.suggested_cached += cached
            calls.append(
                Call(
                    side.weight,
                    side.transcript + prompt,
                    content + reasoning,
                    bool(cached),
                )
            )
            # Only the answer goes back to the model next turn, not its
            # reasoning.
            side.transcript += prompt + content

        cost = turn_cost(calls)
        for pool, chars in cost.items():
            spent[pool] = spent.get(pool, 0) + chars
        if person:
            result.people[person].add(row.created_at, cost)
        result.networks[network].add(row.created_at, cost)
        result.turns += 1
        first = False

    if current is not None:
        result.conversations.append(spent)
    return result


async def _read(days: int) -> tuple[Sequence[Row[Any]], dict[uuid.UUID, float]]:
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
    async with get_session() as session:
        rows = (await session.execute(query)).all()
        weights = {
            llm_id: weight
            for llm_id, weight in (
                await session.execute(select(col(LLMData.id), col(LLMData.cost_weight)))
            ).all()
        }
    return rows, weights


def _line(name: str, values: list[int], limit: int | None = None) -> str:
    if not values:
        return f"{name}: nothing"
    shown = ", ".join(
        f"p{p} {int(v):,}"
        for p, v in zip(PERCENTILES, np.percentile(values, PERCENTILES))
    )
    line = f"{name}: {shown}, max {max(values):,} ({len(values):,})"
    if limit is not None:
        over = sum(value > limit for value in values) / len(values)
        line += f", limit {limit:,}, {over:.1%} over"
    return line


async def limits_calibrate(*, days: int = 30) -> None:
    """
    Replay the comparisons of the last days through the charging rule and
    print what the allowances would have counted: per person and per network
    in each two-hour window, per network in each clock hour, per conversation,
    and the share of answers served from the cache. Read-only.

    Args:
        days: How far back to read
    """
    if not settings.COMPARIA_DB_URI:
        logger.error("COMPARIA_DB_URI is not set, nothing to read")
        raise SystemExit(1)

    rows, weights = await _read(days)
    result = replay(rows, weights)
    logger.info(
        f"{len(result.conversations):,} comparisons and {result.turns:,} turns "
        f"over {days} days; {len(result.people):,} people, "
        f"{len(result.networks):,} networks, {result.unknown_people:,} "
        f"comparisons with no person to count them against"
    )

    limits: dict[tuple[Pool, str], int] = {
        ("all", "session"): settings.RATELIMIT_ALL_PER_SESSION,
        ("all", "ip"): settings.RATELIMIT_ALL_PER_IP,
        ("expensive", "session"): settings.RATELIMIT_EXPENSIVE_PER_SESSION,
        ("expensive", "ip"): settings.RATELIMIT_EXPENSIVE_PER_IP,
    }
    for pool in POOLS:
        people = [w for spend in result.people.values() for w in spend.windows(pool)]
        networks = [
            w for spend in result.networks.values() for w in spend.windows(pool)
        ]
        hours = [h for spend in result.networks.values() for h in spend.hours(pool)]
        conversations = [spent[pool] for spent in result.conversations if pool in spent]
        logger.info(
            _line(f"{pool}, per person and window", people, limits[(pool, "session")])
        )
        logger.info(
            _line(f"{pool}, per network and window", networks, limits[(pool, "ip")])
        )
        logger.info(_line(f"{pool}, per network and hour", hours))
        logger.info(_line(f"{pool}, per conversation", conversations))

    def share(part: int, whole: int) -> str:
        return f"{part / whole:.1%} of {whole:,}" if whole else "none"

    logger.info(
        f"Cached answers: {share(result.cached, result.answers)}; on first "
        f"turns of a suggested prompt: "
        f"{share(result.suggested_cached, result.suggested_answers)}"
    )
