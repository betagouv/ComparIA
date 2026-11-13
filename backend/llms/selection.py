"""
How a selection mode draws the two models of a comparison.

Pure: everything it needs is passed in, so the rules can be checked without a
database, and the admin preview runs the very code the arena runs.
"""

import random
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Any, Iterable, Protocol, Sequence
from uuid import UUID

from backend.errors import NoValidPairError, UnavailableLLMsSelectionError
from backend.llms.models import LLMDataEnabled
from utils.database.models.selection_mode import (
    ModelFilter,
    ModeViability,
    ViabilityWarning,
)
from utils.database.models.utils import utc_now
from utils.ranking.compute import RankingResult

if TYPE_CHECKING:
    from backend.llms.data import LLMsData


def utc_today() -> date:
    """Today in UTC, the clock mode windows are read in, not the host's."""
    return utc_now().date()


# Weight halves for every this many days since release, in "newest" sampling.
NEWEST_HALF_LIFE_DAYS = 180


class ModeRules(Protocol):
    """A mode row, or rules being edited in the admin. Read-only, so that a
    row's Literal fields satisfy it."""

    @property
    def visitor_picks(self) -> int: ...
    @property
    def pool_a(self) -> Any: ...
    @property
    def pool_b(self) -> Any: ...
    @property
    def pairing(self) -> str: ...
    @property
    def sampling(self) -> str: ...
    @property
    def tools_policy(self) -> str: ...
    @property
    def tool_keys(self) -> list[str]: ...


@dataclass
class ToolsOnOffer:
    # Every tool row, and the ones a visitor may get now.
    known: set[str] = field(default_factory=set)
    offered: set[str] = field(default_factory=set)


def as_filter(value: Any) -> ModelFilter | None:
    """A row read back from the database holds a dict, not a ModelFilter."""
    if value is None or isinstance(value, ModelFilter):
        return value
    return ModelFilter.model_validate(value)


def _filters(mode: ModeRules) -> list[ModelFilter]:
    return [f for f in (as_filter(mode.pool_a), as_filter(mode.pool_b)) if f]


def needs_ranking(mode: ModeRules) -> bool:
    return mode.sampling == "fewer_votes" or any(
        f.top_ranked is not None for f in _filters(mode)
    )


def _ranking_entry(ranking: RankingResult | None, llm_id: UUID) -> Any:
    if ranking is None:
        return None
    rankings = ranking.rankings
    return rankings.get(str(llm_id)) or rankings.get(llm_id)


def _ranking_value(entry: Any, name: str) -> Any:
    # The cached ranking is read back as plain dicts; a fresh one holds models.
    if entry is None:
        return None
    if isinstance(entry, dict):
        return entry.get(name)
    return getattr(entry, name, None)


def _top_ranked(
    llms: Sequence[LLMDataEnabled], ranking: RankingResult | None, n: int
) -> set[UUID]:
    ranked = [
        (rank, llm.id)
        for llm in llms
        if (rank := _ranking_value(_ranking_entry(ranking, llm.id), "rank")) is not None
    ]
    return {llm_id for _, llm_id in sorted(ranked)[:n]}


def _matches(llm: LLMDataEnabled, f: ModelFilter, today: date) -> bool:
    # Each field of the model is read only when the filter sets it: some are
    # computed, like the energy class, and cost more than a comparison.
    if f.llm_ids and llm.id not in f.llm_ids:
        return False
    if f.exclude_llm_ids and llm.id in f.exclude_llm_ids:
        return False
    if f.lab_ids and llm.lab_id not in f.lab_ids:
        return False
    if f.exclude_lab_ids and llm.lab_id in f.exclude_lab_ids:
        return False
    if f.tags:
        wanted, tags = set(f.tags), set(llm.tags or [])
        if f.tags_match == "all" and not wanted <= tags:
            return False
        if f.tags_match == "any" and not wanted & tags:
            return False
    if f.exclude_tags and set(llm.tags or []) & set(f.exclude_tags):
        return False
    if f.license_ids and llm.license_id not in f.license_ids:
        return False
    if f.public_weights is not None and llm.public_weights != f.public_weights:
        return False
    if f.eu_hostable is not None and llm.eu_hostable != f.eu_hostable:
        return False
    if f.archs and llm.arch not in f.archs:
        return False
    if f.size_classes and llm.size_class not in f.size_classes:
        return False
    if f.params_min is not None and llm.params < f.params_min:
        return False
    if f.params_max is not None and llm.params > f.params_max:
        return False
    if f.energy_classes and llm.energy_class not in f.energy_classes:
        return False
    if f.inputs and not set(f.inputs) <= set(llm.inputs or []):
        return False
    if f.released_after and llm.release_date < f.released_after:
        return False
    if f.released_before and llm.release_date > f.released_before:
        return False
    if (
        f.released_within_days is not None
        and (today - llm.release_date).days > f.released_within_days
    ):
        return False
    if f.price_out_max is not None and llm.price_out > f.price_out_max:
        return False
    if f.rate_limited is not None and llm.rate_limited != f.rate_limited:
        return False
    if f.arena_tools is not None and llm.arena_tools != f.arena_tools:
        return False
    return True


def filter_pool(
    llms: Iterable[LLMDataEnabled],
    f: ModelFilter | dict,
    ranking: RankingResult | None = None,
    today: date | None = None,
) -> list[UUID]:
    """The models a filter lets through, in catalogue order."""
    f = as_filter(f) or ModelFilter()
    today = today or utc_today()
    llms = list(llms)
    kept = [llm for llm in llms if _matches(llm, f, today)]
    if f.top_ranked is not None:
        # Among every enabled model, not only those the other fields kept:
        # "the 10 best ranked" means the same thing whatever else is set.
        best = _top_ranked(llms, ranking, f.top_ranked)
        kept = [llm for llm in kept if llm.id in best]
    return [llm.id for llm in kept]


def pools(
    mode: ModeRules,
    llms_data: "LLMsData",
    ranking: RankingResult | None = None,
    today: date | None = None,
) -> tuple[list[UUID], list[UUID]]:
    """Pool A and pool B. Without a pool B, both sides draw from pool A."""
    enabled = llms_data.enabled.values()
    pool_a = filter_pool(enabled, mode.pool_a, ranking, today)
    if mode.pool_b is None:
        return pool_a, pool_a
    return pool_a, filter_pool(enabled, mode.pool_b, ranking, today)


def pair_allowed(pairing: str, a: LLMDataEnabled, b: LLMDataEnabled) -> bool:
    if a.id == b.id:
        return False
    if pairing == "different_lab":
        return a.lab_id != b.lab_id
    if pairing == "same_lab":
        return a.lab_id == b.lab_id
    if pairing == "different_size_class":
        return a.size_class != b.size_class
    if pairing == "same_size_class":
        return a.size_class == b.size_class
    return True


def _weight(
    sampling: str, llm: LLMDataEnabled, ranking: RankingResult | None, today: date
) -> float:
    if sampling == "fewer_votes":
        n_match = _ranking_value(_ranking_entry(ranking, llm.id), "n_match") or 0
        return 1 / (1 + n_match)
    if sampling == "newest":
        age = max(0, (today - llm.release_date).days)
        return 0.5 ** (age / NEWEST_HALF_LIFE_DAYS)
    return 1.0


def weighted_choice(
    mode: ModeRules,
    candidates: Sequence[UUID],
    llms_data: "LLMsData",
    ranking: RankingResult | None = None,
    rng: Any = None,
    today: date | None = None,
) -> UUID:
    rng = rng or random
    today = today or utc_today()
    if mode.sampling == "uniform":
        return rng.choice(list(candidates))
    enabled = llms_data.enabled
    weights = [
        _weight(mode.sampling, enabled[llm_id], ranking, today) for llm_id in candidates
    ]
    return rng.choices(list(candidates), weights=weights, k=1)[0]


def count_pairs(
    mode: ModeRules,
    pool_a: Sequence[UUID],
    pool_b: Sequence[UUID],
    llms_data: "LLMsData",
) -> int:
    enabled = llms_data.enabled
    pairs = {
        frozenset((a, b))
        for a in pool_a
        for b in pool_b
        if pair_allowed(mode.pairing, enabled[a], enabled[b])
    }
    return len(pairs)


def picker_llm_ids(
    mode: ModeRules,
    llms_data: "LLMsData",
    ranking: RankingResult | None = None,
    today: date | None = None,
) -> list[UUID]:
    """
    The models the arena's picker lists: every model in the pools that the
    pairing rule lets face a model of the other pool. Locked ones (not
    custom_selectable) are listed too, greyed out, so a visitor sees they only
    come up at random; the draw still refuses them as a pick.
    """
    pool_a, pool_b = pools(mode, llms_data, ranking, today)
    enabled = llms_data.enabled

    def pairable(llm_id: UUID, others: Sequence[UUID]) -> bool:
        return any(
            pair_allowed(mode.pairing, enabled[llm_id], enabled[other])
            for other in others
        )

    return list(
        dict.fromkeys(
            [
                *(llm_id for llm_id in pool_a if pairable(llm_id, pool_b)),
                *(llm_id for llm_id in pool_b if pairable(llm_id, pool_a)),
            ]
        )
    )


def _check_picks(
    mode: ModeRules,
    picked: Sequence[UUID],
    llms_data: "LLMsData",
    pool_a: Sequence[UUID],
    pool_b: Sequence[UUID],
) -> list[UUID]:
    picks = list(dict.fromkeys(picked))
    if len(picks) != len(picked) or len(picks) > mode.visitor_picks:
        raise UnavailableLLMsSelectionError("More models picked than the mode allows")
    enabled = llms_data.enabled
    if [llm_id for llm_id in picks if llm_id not in enabled]:
        raise UnavailableLLMsSelectionError(
            "Custom LLMs selection contains unavailable LLMs"
        )
    # The arena greys these out, so only a client skipping it gets here.
    if [llm_id for llm_id in picks if not enabled[llm_id].custom_selectable]:
        raise UnavailableLLMsSelectionError(
            "Custom LLMs selection contains locked LLMs"
        )
    if [llm_id for llm_id in picks if llm_id not in pool_a and llm_id not in pool_b]:
        raise UnavailableLLMsSelectionError(
            "Custom LLMs selection is outside the mode's pools"
        )
    # With two pools, a pair of picks still needs one model from each: the
    # pairing rule is waived for the visitor, the split is not.
    if len(picks) == 2 and mode.pool_b is not None:
        a, b = picks
        if not ((a in pool_a and b in pool_b) or (b in pool_a and a in pool_b)):
            raise UnavailableLLMsSelectionError(
                "Custom LLMs selection does not take one model from each pool"
            )
    return picks


def _draw(
    mode: ModeRules,
    pool_a: Sequence[UUID],
    pool_b: Sequence[UUID],
    picks: Sequence[UUID],
    llms_data: "LLMsData",
    ranking: RankingResult | None,
    rng: Any,
    today: date,
) -> tuple[UUID, UUID]:
    enabled = llms_data.enabled

    def partners(llm_id: UUID, pool: Sequence[UUID]) -> list[UUID]:
        return [
            other
            for other in pool
            if pair_allowed(mode.pairing, enabled[llm_id], enabled[other])
        ]

    def choose(candidates: Sequence[UUID]) -> UUID:
        return weighted_choice(mode, candidates, llms_data, ranking, rng, today)

    if picks:
        picked = picks[0]
        # The other side comes from the pool the pick is not in.
        options = partners(picked, pool_b) if picked in pool_a else []
        if not options and picked in pool_b:
            options = partners(picked, pool_a)
        if not options:
            raise NoValidPairError("No model can be drawn against the pick")
        return picked, choose(options)

    # Only models with at least one allowed partner may come first, so a
    # pairing rule never fails a draw that some pair could satisfy.
    firsts = [llm_id for llm_id in pool_a if partners(llm_id, pool_b)]
    if not firsts:
        raise NoValidPairError("The mode has no valid pair")
    first = choose(firsts)
    return first, choose(partners(first, pool_b))


def draw_pair(
    mode: ModeRules,
    llms_data: "LLMsData",
    picked: Sequence[UUID] = (),
    unavailable: Iterable[UUID] = (),
    ranking: RankingResult | None = None,
    rng: Any = None,
    today: date | None = None,
) -> tuple[UUID, UUID]:
    """
    Two different models for a comparison, in random order.

    Raises UnavailableLLMsSelectionError when the visitor's picks are not
    allowed, and NoValidPairError when no pair meets the mode's rules.
    """
    rng = rng or random
    today = today or utc_today()
    pool_a, pool_b = pools(mode, llms_data, ranking, today)
    picks = _check_picks(mode, picked, llms_data, pool_a, pool_b)

    if len(picks) == 2:
        pair = (picks[0], picks[1])
    else:
        # Unavailable models are left out when the pools allow it.
        down = set(unavailable)
        try:
            pair = _draw(
                mode,
                [llm_id for llm_id in pool_a if llm_id not in down],
                [llm_id for llm_id in pool_b if llm_id not in down],
                picks,
                llms_data,
                ranking,
                rng,
                today,
            )
        except NoValidPairError:
            if not down:
                raise
            pair = _draw(mode, pool_a, pool_b, picks, llms_data, ranking, rng, today)

    # Random swap, so that the side tells nothing about the pool or the pick.
    if rng.random() < 0.5:
        return pair[1], pair[0]
    return pair


def replacement_pool(
    mode: ModeRules,
    llms_data: "LLMsData",
    failing: UUID,
    other: UUID,
    ranking: RankingResult | None = None,
    today: date | None = None,
) -> list[UUID]:
    """
    The models that may take over from a failing one: from the pool it came
    from, and still a valid pair with the model that stays.
    """
    pool_a, pool_b = pools(mode, llms_data, ranking, today)
    in_a, in_b = failing in pool_a, failing in pool_b
    if in_a and not in_b:
        pool = pool_a
    elif in_b and not in_a:
        pool = pool_b
    elif other in pool_a and other not in pool_b:
        pool = pool_b
    elif other in pool_b and other not in pool_a:
        pool = pool_a
    else:
        pool = list(dict.fromkeys([*pool_a, *pool_b]))

    enabled = llms_data.enabled
    if other not in enabled:
        return [llm_id for llm_id in pool if llm_id not in (failing, other)]
    return [
        llm_id
        for llm_id in pool
        if llm_id != failing
        and pair_allowed(mode.pairing, enabled[llm_id], enabled[other])
    ]


def viability(
    mode: ModeRules,
    llms_data: "LLMsData",
    ranking: RankingResult | None = None,
    tools: ToolsOnOffer | None = None,
    today: date | None = None,
) -> ModeViability:
    """
    Whether the mode can draw a pair now. Tools are only checked when `tools`
    is given, which the arena skips for modes that cannot be short of one.
    """
    pool_a, pool_b = pools(mode, llms_data, ranking, today)
    pairs = count_pairs(mode, pool_a, pool_b, llms_data)
    warnings: list[ViabilityWarning] = []
    if not pool_a:
        warnings.append("pool_a_empty")
    if mode.pool_b is not None and not pool_b:
        warnings.append("pool_b_empty")
    if pool_a and pool_b and pairs == 0:
        warnings.append("no_valid_pair")
    if pairs == 1:
        warnings.append("single_pair")
    named = {
        llm_id for f in _filters(mode) for llm_id in [*f.llm_ids, *f.exclude_llm_ids]
    }
    if named - set(llms_data.enabled):
        warnings.append("unknown_llm_ids")

    viable = pairs > 0
    if tools is not None and mode.tools_policy != "none" and mode.tool_keys:
        if set(mode.tool_keys) - tools.known:
            warnings.append("unknown_tool_keys")
        if set(mode.tool_keys) - tools.offered:
            warnings.append("tool_not_offered")
        # A mode sold as "always with web search" must not run without it.
        if mode.tools_policy == "forced" and not set(mode.tool_keys) & tools.offered:
            viable = False

    return ModeViability(
        viable=viable,
        pool_a_size=len(pool_a),
        pool_b_size=len(pool_b),
        pairs=pairs,
        warnings=warnings,
    )


def enabled_tools(
    mode: ModeRules, requested: Sequence[str], offered: Sequence[str]
) -> list[str]:
    """
    The tools a new comparison runs with. Stored on the comparison, so every
    later turn and retry keeps them.
    """
    if mode.tools_policy == "none":
        return []
    if mode.tools_policy == "forced":
        return [key for key in mode.tool_keys if key in offered]
    kept = [key for key in dict.fromkeys(requested) if key in offered]
    if mode.tool_keys:
        kept = [key for key in kept if key in mode.tool_keys]
    return kept


def allowed_tools(mode: ModeRules, offered: Sequence[str]) -> list[str]:
    """The tools a visitor sees in this mode: forced ones, or ones to choose."""
    if mode.tools_policy == "none":
        return []
    if mode.tools_policy == "forced" or mode.tool_keys:
        return [key for key in mode.tool_keys if key in offered]
    return list(offered)
