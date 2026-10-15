"""
The limit rules of the arena routes, on top of the counters in `limits`: what
a refused message is told, what the person meets before typing, and what each
side of a turn is charged.
"""

from datetime import datetime, timedelta, timezone
from typing import Collection, Literal, Mapping, Sequence
from uuid import UUID

from backend.arena.limits import (
    Allowance,
    Answer,
    Call,
    Day,
    LimitStatus,
    expected_answer_chars,
)
from backend.arena.litellm import sent_chars
from backend.arena.models import ArenaLimits, LimitRefusal, PausedLLM, SpentAllowance
from backend.arena.streaming import get_messages
from backend.errors import LimitReachedError
from backend.llms.data import LLMsData, NoModelLeft
from utils.database.models import BOT_POS, BotPos, ComparisonRead, TurnRead


def lifts_last(spent: Sequence[Allowance]) -> tuple[Allowance, datetime | None]:
    """The spent allowance that lifts last, since that is when the person can
    go on, and the time it lifts, None when unknown. One with no known reset
    counts as the last."""
    last = max(
        spent,
        key=lambda allowance: (allowance.resets_in is None, allowance.resets_in or 0),
    )
    if last.resets_in is None:
        return last, None
    if last.expires_at is not None:
        return last, datetime.fromtimestamp(last.expires_at, timezone.utc)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return last, now + timedelta(seconds=last.resets_in)


def public_scope(allowance: Allowance) -> Literal["session", "network"]:
    return "session" if allowance.scope == "session" else "network"


def limit_refusal(
    spent: Sequence[Allowance], llm_ids: Sequence[UUID] = ()
) -> LimitReachedError:
    """
    What the person is told for these spent allowances: the one that lifts
    last. `llm_ids` are the models the person picked and may not use until
    then.
    """
    last, resets_at = lifts_last(spent)
    return LimitReachedError(
        "allowance_spent" if last.pool == "all" else "expensive_allowance_spent",
        LimitRefusal(
            scope=public_scope(last),
            resets_at=resets_at,
            resets_in=last.resets_in,
            llm_ids=list(llm_ids),
        ),
    )


def full_refusal(
    resting: Mapping[UUID, datetime], llm_ids: Sequence[UUID] = ()
) -> LimitReachedError:
    """A new comparison refused on models whose daily cap is full, for
    everyone: the picked ones in `llm_ids`, or a mode left with nothing to
    draw. They come back at midnight in Paris."""
    return LimitReachedError(
        "model_full_today",
        LimitRefusal(
            scope=None,
            resets_at=min(resting.values(), default=Day.at().ends),
            resets_in=Day.at().ends_in(),
            llm_ids=list(llm_ids),
        ),
    )


def pick_refusal(
    error: NoModelLeft,
    resting: Mapping[UUID, datetime],
    spent: Sequence[Allowance],
    expensive: Collection[UUID] = (),
) -> LimitReachedError:
    """
    What the person is told when a draw has nothing left, `spent` holding
    the expensive allowances that left the `expensive` models out, if any.

    When both limits apply, to a model picked that is full and expensive, to
    two picked models one each way, or to a mode left with nothing, the one
    that lifts last is told, with every model picked: that is when the pick
    can go through.
    """
    picked = error.llm_ids
    full = (not picked and bool(resting)) or any(i in resting for i in picked)
    paused = bool(spent) and (not picked or any(i in expensive for i in picked))
    if paused and not full:
        return limit_refusal(spent, picked)
    if full and paused:
        # An allowance with no known end lifts last.
        lifts = lifts_last(spent)[1]
        if lifts is None or lifts > min(resting.values()):
            return limit_refusal(spent, picked)
    return full_refusal(resting, picked)


def arena_limits(
    limit_status: LimitStatus,
    expensive_models: Sequence[UUID],
    full: Mapping[UUID, datetime] | None = None,
) -> ArenaLimits:
    """
    The limits a person meets before typing. Of the allowances spent in one
    pool, the one that lifts last is told, as in a refusal.

    `full` holds each model whose daily cap is full and when it lifts. A model
    paused both ways is listed once, by the pause that lasts longer.
    """
    total = spent_allowance(limit_status.spent_in("all"))
    expensive = spent_allowance(limit_status.spent_in("expensive"))

    paused: dict[UUID, PausedLLM] = {}
    if expensive:
        paused = {
            llm_id: PausedLLM(id=llm_id, until=expensive.resets_at, reason="allowance")
            for llm_id in expensive_models
        }
    for llm_id, until in (full or {}).items():
        other = paused.get(llm_id)
        # An allowance pause with no known end is the longest there is.
        if other is None or (other.until is not None and until > other.until):
            paused[llm_id] = PausedLLM(id=llm_id, until=until, reason="full")

    return ArenaLimits(
        total=total, expensive=expensive, paused_llms=list(paused.values())
    )


def spent_allowance(spent: Sequence[Allowance]) -> SpentAllowance | None:
    """What is told of a pool's spent allowances, None while none is spent."""
    if not spent:
        return None
    last, resets_at = lifts_last(spent)
    return SpentAllowance(
        scope=public_scope(last), resets_at=resets_at, resets_in=last.resets_in
    )


# What each side of a turn is sent: its model and the characters.
Sent = Mapping[BotPos, tuple[UUID, int]]


def first_turn_sent(prompt: str, pair: tuple[UUID, UUID], llms_data: LLMsData) -> Sent:
    """What each model of a new comparison is sent, before any web search."""
    return {
        pos: (llm_id, len(llms_data.all[llm_id].system_prompt or "") + len(prompt))
        for pos, llm_id in zip(BOT_POS, pair)
    }


def follow_up_sent(comparison: ComparisonRead, message: str = "") -> Sent:
    """What each model is sent to answer the last turn, or `message` after it:
    the system prompt, every turn so far and that side's earlier answers."""
    return {
        pos: (
            getattr(comparison, f"llm_id_{pos}"),
            sent_chars(get_messages(comparison, pos)) + len(message),
        )
        for pos in BOT_POS
    }


def turn_calls(sent: Sent, llms_data: LLMsData) -> dict[BotPos, Call]:
    """Each side as reserved: what it is sent, and a typical answer."""
    return {
        pos: Call.of(llms_data.all[llm_id], chars, written=expected_answer_chars())
        for pos, (llm_id, chars) in sent.items()
    }


def answers(turn: TurnRead | None) -> dict[BotPos, Answer | None]:
    """What each model wrote this turn, so far if it was cut short."""
    return {pos: getattr(turn, f"llm_msg_{pos}", None) for pos in BOT_POS}
