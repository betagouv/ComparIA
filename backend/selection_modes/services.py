"""
Selection modes as the arena reads them: which ones a visitor is offered, and
which one a new comparison runs under.
"""

import logging
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlmodel import col, select

from backend.arena.tools import get_offered_tools
from backend.config import DEFAULT_SELECTION_MODE, KNOWN_COHORTS
from backend.llms.data import LLMsData, get_llms_data
from backend.llms.selection import (
    ModeRules,
    ToolsOnOffer,
    allowed_tools,
    as_filter,
    enabled_tools,
    needs_ranking,
    picker_llm_ids,
    pools,
    replacement_pool,
    viability,
    weighted_choice,
)
from backend.utils.countries import get_ranking
from backend.utils.locale import get_locales_settings, pick_translation
from utils.database.models import (
    BotPos,
    ComparisonRead,
    SelectionMode,
    SelectionModeBase,
    SelectionModePublic,
)
from utils.database.models.selection_mode import SelectionModeRules
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.i18n import SupportedLocale
from utils.ranking.compute import RankingResult
from utils.storage.redis import REDIS_SELECTION_MODES_KEY, redis_cache

logger = logging.getLogger("languia")


# What a visitor gets when no mode is on offer for them.
PLAIN_DRAW = SelectionModeBase(
    key=DEFAULT_SELECTION_MODE, label={}, icon="i-ri-dice-line"
)


class ModeUnavailableError(ValueError):
    """The mode a request names is unknown, switched off, out of its window,
    not meant for this visitor, or cannot draw a pair."""


@redis_cache(REDIS_SELECTION_MODES_KEY)
async def get_selection_modes() -> list[SelectionModeBase]:
    """Every mode, in menu order. Invalidated by each admin write."""
    async with get_session() as session:
        rows = await session.exec(
            select(SelectionMode).order_by(
                col(SelectionMode.position), col(SelectionMode.created_at)
            )
        )
        return [SelectionModeBase.model_validate(row) for row in rows.all()]


async def find_selection_mode(key: str) -> SelectionModeBase | None:
    return next((mode for mode in await get_selection_modes() if mode.key == key), None)


def parse_cohorts(cohorts: str | None) -> set[str]:
    """The cohorts a client declares, comma-separated as in `?c=`."""
    return {cohort.strip() for cohort in (cohorts or "").split(",") if cohort.strip()}


async def keep_known_cohorts(cohorts: str | None) -> str:
    """
    The declared cohorts a comparison may record: the known ones and those a
    selection mode names, sorted. The rest came from a URL and is dropped.
    """
    known = set(KNOWN_COHORTS) | {
        cohort for mode in await get_selection_modes() for cohort in mode.cohorts
    }
    return ",".join(sorted(parse_cohorts(cohorts) & known))


def in_audience(
    mode: SelectionModeBase,
    now: datetime,
    locale: SupportedLocale | None,
    cohorts: set[str],
) -> bool:
    """
    Whether the mode is meant for this visitor now. Cohorts are declared by
    the client, so a cohort mode hides itself from other visitors but is no
    secret from a determined one.
    """
    if not mode.enabled:
        return False
    if mode.starts_at and now < mode.starts_at:
        return False
    if mode.ends_at and now >= mode.ends_at:
        return False
    if mode.locales and locale is not None and locale not in mode.locales:
        return False
    if mode.cohorts and not set(mode.cohorts) & cohorts:
        return False
    return True


def default_mode(modes: Sequence[SelectionModeBase]) -> SelectionModeBase | None:
    """The marked default, else the old default key, else the first mode."""
    return (
        next((mode for mode in modes if mode.is_default), None)
        or next((mode for mode in modes if mode.key == DEFAULT_SELECTION_MODE), None)
        or next(iter(modes), None)
    )


async def _offered_tool_keys() -> list[str]:
    return [tool.key for tool in await get_offered_tools()]


def _viable_keys(
    modes: list[SelectionModeBase],
    llms_data: LLMsData,
    offered: list[str],
    ranking: RankingResult | None,
) -> set[str]:
    tools = ToolsOnOffer(known=set(offered), offered=set(offered))
    return {
        mode.key
        for mode in modes
        if mode.enabled and viability(mode, llms_data, ranking, tools).viable
    }


async def modes_on_offer(
    locale: SupportedLocale | None,
    cohorts: str | None,
    llms_data: LLMsData | None = None,
    offered: list[str] | None = None,
) -> list[SelectionModeBase]:
    """The modes a visitor is offered, in menu order: meant for them and able
    to draw a pair."""
    now = utc_now()
    declared = parse_cohorts(cohorts)
    all_modes = await get_selection_modes()
    modes = [mode for mode in all_modes if in_audience(mode, now, locale, declared)]
    if not modes:
        return []
    llms_data = llms_data or await get_llms_data()
    offered = offered if offered is not None else await _offered_tool_keys()
    enabled = [mode for mode in all_modes if mode.enabled]
    ranking = get_ranking() if any(needs_ranking(mode) for mode in enabled) else None
    viable = _viable_keys(all_modes, llms_data, offered, ranking)
    return [mode for mode in modes if mode.key in viable]


def _split_pools(
    mode: SelectionModeBase, llms_data: LLMsData, ranking: RankingResult | None
) -> dict[str, list[UUID]]:
    """Both pools, for a mode where two picks must take one from each."""
    if mode.visitor_picks < 2 or mode.pool_b is None:
        return {}
    pool_a, pool_b = pools(mode, llms_data, ranking)
    return {"llm_ids_a": pool_a, "llm_ids_b": pool_b}


async def get_public_modes(
    locale: SupportedLocale, cohorts: str | None
) -> list[SelectionModePublic]:
    llms_data = await get_llms_data()
    offered = await _offered_tool_keys()
    modes = await modes_on_offer(locale, cohorts, llms_data, offered)
    default = default_mode(modes)
    locales = await get_locales_settings()
    ranking = get_ranking() if any(needs_ranking(mode) for mode in modes) else None

    public = []
    for mode in modes:
        try:
            label = pick_translation(mode.label, locale, locales)[1]
        except ValueError:
            label = mode.key
        try:
            short_label = pick_translation(mode.short_label, locale, locales)[1]
        except ValueError:
            short_label = label
        try:
            description: str | None = pick_translation(
                mode.description, locale, locales
            )[1]
        except ValueError:
            description = None
        public.append(
            SelectionModePublic(
                key=mode.key,
                label=label,
                short_label=short_label,
                description=description,
                icon=mode.icon,
                is_default=mode is default,
                visitor_picks=mode.visitor_picks,
                tools_policy=mode.tools_policy,
                tool_keys=allowed_tools(mode, offered),
                # The pools of a blind mode stay on the server.
                llm_ids=(
                    picker_llm_ids(mode, llms_data, ranking)
                    if mode.visitor_picks
                    else None
                ),
                **_split_pools(mode, llms_data, ranking),
            )
        )
    return public


async def resolve_mode(
    key: str | None,
    locale: SupportedLocale | None,
    cohorts: str | None,
) -> SelectionModeBase:
    """
    The mode a new comparison runs under, or ModeUnavailableError. Without a
    key, the default mode on offer, or a plain draw when none is. Whether the
    mode can draw a pair is left to the draw itself, which fails with
    NoValidPairError.
    """
    if key is None:
        # Nothing on offer for this visitor (every mode limited to an
        # audience, out of its window or unable to draw): a plain draw over
        # the whole catalogue, rather than refusing every first message.
        return default_mode(await modes_on_offer(locale, cohorts)) or PLAIN_DRAW

    mode = await find_selection_mode(key)
    if mode is None or not in_audience(mode, utc_now(), locale, parse_cohorts(cohorts)):
        raise ModeUnavailableError(f"Mode '{key}' is not on offer")
    if mode.tools_policy == "forced":
        offered = await _offered_tool_keys()
        if not set(mode.tool_keys) & set(offered):
            raise ModeUnavailableError(f"Mode '{key}' has none of its tools on offer")
    return mode


def _draw_rules(mode: SelectionModeBase) -> tuple:
    return (
        as_filter(mode.pool_a),
        as_filter(mode.pool_b),
        mode.pairing,
        mode.sampling,
        mode.tools_policy,
        sorted(mode.tool_keys),
    )


async def comparison_mode_key(
    mode: SelectionModeBase, picked: Sequence[str] | None
) -> str:
    """
    The mode key a comparison records. A visitor who opens a pick mode and
    picks nothing gets the very draw of the default mode when the rules match
    (the seeded "custom" against "random"): the dataset has always called that
    the default mode, so it still does. With other rules the draw differs, and
    the mode keeps its own key.
    """
    if not mode.visitor_picks or picked:
        return mode.key
    default = default_mode(
        [other for other in await get_selection_modes() if other.enabled]
    )
    if (
        default is not None
        and not default.visitor_picks
        and _draw_rules(default) == _draw_rules(mode)
    ):
        return default.key
    return mode.key


async def tools_for_comparison(
    mode: SelectionModeBase, requested: list[str]
) -> list[str]:
    """
    The tools a new comparison gets under its mode's policy. A mode with no
    tools never reads the request's list at all.
    """
    if mode.tools_policy == "none":
        return []
    if mode.tools_policy == "visitor" and not requested:
        return []
    return enabled_tools(mode, requested, await _offered_tool_keys())


async def pick_replacement_model(
    comparison: ComparisonRead, pos: BotPos, charged: bool = False
) -> UUID | None:
    """
    Pick a model to take over from a failing one, from the pool it was drawn
    from under the comparison's mode. A mode deleted since leaves the whole
    catalogue to draw from.

    `charged` says the turn already paid its character budgets for the current
    pair. If neither model is pricey, the turn skipped the pricey budget, so
    no pricey model may take over.
    """
    models = await get_llms_data()
    other_pos: BotPos = "b" if pos == "a" else "a"
    failing = getattr(comparison, f"llm_id_{pos}")
    other = getattr(comparison, f"llm_id_{other_pos}")

    mode: ModeRules = await find_selection_mode(comparison.mode) or SelectionModeRules()
    ranking = get_ranking() if needs_ranking(mode) else None
    pool = replacement_pool(mode, models, failing, other, ranking)

    pricey = models.pricey_models
    if charged and failing not in pricey and other not in pricey:
        pool = [llm_id for llm_id in pool if llm_id not in pricey]

    if not pool:
        logger.warning("No model can take over from a failing one")
        return None
    return weighted_choice(mode, pool, models, ranking)
