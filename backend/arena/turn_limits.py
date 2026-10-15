"""
The limit rules of the arena routes, on top of the counters in `limits`. A
route that calls the models asks one function here and does what it says:

- `check_allowance`, before anything else: a spent whole allowance stops
  every message.
- `start_first_turn` draws the pair of a new comparison and charges its first
  message. Once the expensive allowance is spent, the draw leaves expensive
  models out instead of refusing the message, and a model whose daily cap is
  full is left out of every draw until midnight.
- `charge_follow_up` charges a follow-up or a retry. Only the whole allowance
  refuses it: a conversation under way finishes, since refusing it would tell
  the person, before the reveal, what is in the pair.

`read_arena_limits` is what the person meets before typing. Each refusal is a
`Refused`, which the router answers with a 429.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Collection, Literal, Mapping, Sequence
from uuid import UUID

from backend.arena.limits import (
    POOLS,
    Allowance,
    AllowanceSpent,
    Answer,
    Call,
    Charge,
    Day,
    Identity,
    LimitStatus,
    Pool,
    expected_answer_chars,
    expensive_models,
    read_status,
    resting_models,
)
from backend.arena.litellm import sent_chars
from backend.arena.models import (
    ArenaLimits,
    LimitKey,
    LimitRefusal,
    PausedLLM,
    SpentAllowance,
)
from backend.arena.streaming import get_messages
from backend.config import CustomModelsSelection, SelectionMode
from backend.llms.data import LLMsData, NoModelLeft
from utils.database.models import BOT_POS, BotPos, ComparisonRead, TurnRead


class Refused(Exception):
    """A message refused on a limit: its key, what the person is told, and
    why, for the logs."""

    def __init__(self, key: LimitKey, limit: LimitRefusal, reason: str) -> None:
        super().__init__(reason)
        self.key = key
        self.limit = limit


def check_allowance(who: Identity) -> LimitStatus:
    """
    The person's allowances, read before anything else runs. Only the whole
    one stops a message here: a spent expensive one keeps expensive models
    out of new comparisons, see `start_first_turn`, which takes the status
    read here.

    Raises:
        Refused: while the whole allowance is spent
    """
    status = read_status(who)
    if spent := status.spent_in("all"):
        raise limit_refusal(spent)
    return status


@dataclass(frozen=True)
class FirstTurn:
    pair: tuple[UUID, UUID]
    # Whether expensive models were open to the draw.
    expensive_available: bool
    # To settle once the models have answered.
    charge: Charge


def start_first_turn(
    who: Identity,
    status: LimitStatus,
    llms_data: LLMsData,
    mode: SelectionMode,
    selection: CustomModelsSelection,
    prompt: str,
) -> FirstTurn:
    """
    Draw the two models of a new comparison and charge its first message.
    `status` is the one `check_allowance` read. A custom pick of a model left
    out is refused with its id, as is a mode left with nothing to draw.

    Raises:
        Refused: on a spent whole allowance, or a draw with nothing left
    """
    resting = resting_models(llms_data.enabled.values())
    expensive = expensive_models(llms_data.enabled.values())

    def draw(spent: Sequence[Allowance]) -> tuple[UUID, UUID]:
        excluded = [*resting, *(expensive if spent else [])]
        try:
            return llms_data.pick_two(mode, selection, hard_excluded=excluded)
        except NoModelLeft as error:
            raise pick_refusal(
                error,
                resting,
                spent,
                expensive,
                f"a '{mode}' draw with {len(resting)} models full today and"
                f" expensive models {'out' if spent else 'in'},"
                f" picks left out: [{error}]",
            )

    def without_expensive(spent: Sequence[Allowance]) -> FirstTurn:
        pair = draw(spent)
        sent = first_turn_sent(prompt, pair, llms_data)
        return FirstTurn(pair, False, charge(who, sent, llms_data))

    if not status.expensive_available:
        return without_expensive(status.spent_in("expensive"))

    pair = draw(())
    sent = first_turn_sent(prompt, pair, llms_data)
    try:
        return FirstTurn(pair, True, Charge.reserve(who, turn_calls(sent, llms_data)))
    except AllowanceSpent as error:
        if whole := [a for a in error.spent if a.pool == "all"]:
            # Only the whole allowance is told: the expensive one says to
            # pick other models, which would not help.
            raise limit_refusal(whole)
        # Another message spent the expensive allowance since it was read.
        return without_expensive(error.spent)


def charge_follow_up(
    who: Identity, comparison: ComparisonRead, llms_data: LLMsData, message: str = ""
) -> Charge:
    """
    Charge a follow-up `message`, or a retry of the last turn with none. A
    conversation under way finishes even once the expensive allowance is
    spent, and its turns still count against it, so only the whole allowance
    refuses it. A retry is sent the whole input again: the provider billed
    the failed attempt.

    Raises:
        Refused: while the whole allowance is spent
    """
    whole: tuple[Pool] = ("all",)
    return charge(who, follow_up_sent(comparison, message), llms_data, whole)


def read_arena_limits(who: Identity, llms_data: LLMsData) -> ArenaLimits:
    """What the person meets before typing, see `arena_limits`."""
    status = read_status(who)
    expensive: list[UUID] = []
    if not status.expensive_available:
        expensive = expensive_models(llms_data.enabled.values())
    return arena_limits(status, expensive, resting_models(llms_data.enabled.values()))


def charge(
    who: Identity,
    sent: "Sent",
    llms_data: LLMsData,
    refusing: Collection[Pool] = POOLS,
) -> Charge:
    """
    Spend what each model is sent, and a typical answer, before any model is
    called; the route settles it to what they wrote once the turn is over. No
    refund when a model then fails: an error a client can provoke would buy
    whatever the models had already written. Only the pools in `refusing`
    may refuse the message, see `limits.reserve`.

    Raises:
        Refused: with the allowances that refused
    """
    try:
        return Charge.reserve(who, turn_calls(sent, llms_data), refusing)
    except AllowanceSpent as error:
        raise limit_refusal(error.spent)


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
    spent: Sequence[Allowance], llm_ids: Sequence[UUID] = (), reason: str = ""
) -> Refused:
    """
    What the person is told for these spent allowances: the one that lifts
    last. `llm_ids` are the models the person picked and may not use until
    then.
    """
    last, resets_at = lifts_last(spent)
    return Refused(
        "allowance_spent" if last.pool == "all" else "expensive_allowance_spent",
        LimitRefusal(
            scope=public_scope(last),
            resets_at=resets_at,
            resets_in=last.resets_in,
            llm_ids=list(llm_ids),
        ),
        reason or f"the {last.pool} allowance is spent per {last.scope}",
    )


def full_refusal(
    resting: Mapping[UUID, datetime], llm_ids: Sequence[UUID] = (), reason: str = ""
) -> Refused:
    """A new comparison refused on models whose daily cap is full, for
    everyone: the picked ones in `llm_ids`, or a mode left with nothing to
    draw. They come back at midnight in Paris."""
    day = Day.at()
    return Refused(
        "model_full_today",
        LimitRefusal(
            scope=None,
            resets_at=min(resting.values(), default=day.ends),
            resets_in=day.ends_in(),
            llm_ids=list(llm_ids),
        ),
        reason or "the models are full today",
    )


def pick_refusal(
    error: NoModelLeft,
    resting: Mapping[UUID, datetime],
    spent: Sequence[Allowance],
    expensive: Collection[UUID] = (),
    reason: str = "",
) -> Refused:
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
        return limit_refusal(spent, picked, reason)
    if full and paused:
        # An allowance with no known end lifts last.
        lifts = lifts_last(spent)[1]
        if lifts is None or lifts > min(resting.values()):
            return limit_refusal(spent, picked, reason)
    return full_refusal(resting, picked, reason)


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


def turn_calls(sent: Sent, llms_data: LLMsData) -> dict[str, Call]:
    """Each side as reserved: what it is sent, and a typical answer."""
    return {
        pos: Call.of(llms_data.all[llm_id], chars, written=expected_answer_chars())
        for pos, (llm_id, chars) in sent.items()
    }


def answers(turn: TurnRead | None) -> dict[str, Answer | None]:
    """What each model wrote this turn, so far if it was cut short."""
    return {pos: getattr(turn, f"llm_msg_{pos}", None) for pos in BOT_POS}
