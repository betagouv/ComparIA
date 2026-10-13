import logging
from typing import TYPE_CHECKING, Annotated, Any, Sequence
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field, computed_field, field_validator
from sqlmodel import select

from backend.config import (
    BIG_MODELS_BUCKET_LOWER_LIMIT,
    SMALL_MODELS_BUCKET_UPPER_LIMIT,
    CustomModelsSelection,
    SelectionMode,
)
from backend.llms.currency import CurrencyInfo, get_currency_info
from backend.llms.models import APILLMData, LLMDataArchived, LLMDataEnabled
from backend.utils.countries import get_ranking
from utils.database.encrypted import UnreadableRow, UnreadableSecret
from utils.database.models.llms import LLMData
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.storage.redis import REDIS_LLMS_DATA_CACHE_KEY, redis_cache

if TYPE_CHECKING:
    from utils.database.models import BotPos, ComparisonRead

logger = logging.getLogger("languia")


class NoModelLeft(Exception):
    """
    A draw that its hard exclusions leave nothing to pick from, or a custom
    pick of models that are excluded (in `llm_ids`).
    """

    def __init__(self, llm_ids: Sequence[UUID] = ()) -> None:
        super().__init__(", ".join(str(llm_id) for llm_id in llm_ids))
        self.llm_ids = list(llm_ids)


class LLMsData(BaseModel):
    all: dict[
        UUID,
        Annotated[LLMDataEnabled | LLMDataArchived, Field(discriminator="status")],
    ]

    @field_validator("all", mode="before")
    @classmethod
    def filter_disabled(cls, llms: Any) -> dict[str, Any]:
        """
        Filter out disabled LLMs: the ones without an endpoint, without a key,
        and the ones whose key no configured encryption key opens. The last
        case is an operator's mistake and is logged as such, once per
        endpoint; the rest of the arena keeps running without those models.
        """
        kept: dict[str, Any] = {}
        unreadable: set[Any] = set()
        for llm in llms:
            if llm.status == "archived":
                kept[llm.id] = llm
                continue
            if llm.status != "enabled" or llm.endpoint is None:
                continue
            api_key = llm.endpoint.api_key
            if api_key is None:
                continue
            if isinstance(api_key, UnreadableSecret):
                if llm.endpoint.id not in unreadable:
                    unreadable.add(llm.endpoint.id)
                    ref = UnreadableRow("llm_endpoint", llm.endpoint.id, "api_key")
                    logger.error(
                        f"[SECRETS] {ref.message()}: the models of "
                        f"'{llm.endpoint.name}' are disabled"
                    )
                continue
            kept[llm.id] = llm
        return kept

    @computed_field  # type: ignore[prop-decorator]
    @property
    def enabled(self) -> dict[str, LLMDataEnabled]:
        """
        Filter to only enabled models (removes disabled or deprecated models)
        """
        return {
            model.id: model
            for model in self.all.values()
            if isinstance(model, LLMDataEnabled)
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def random_models(self) -> list[UUID]:
        """
        All models (for standard random selection)
        """
        return [model.id for model in self.enabled.values()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def small_models(self) -> list[UUID]:
        """
        Models with parameters <= 60B (for "small-models" selection mode)
        """
        return [
            model.id
            for model in self.enabled.values()
            if model.params <= SMALL_MODELS_BUCKET_UPPER_LIMIT
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def big_models(self) -> list[UUID]:
        """
        Models with parameters >= 100B (for "big-vs-small" selection mode)
        """
        return [
            model.id
            for model in self.enabled.values()
            if model.params >= BIG_MODELS_BUCKET_LOWER_LIMIT
        ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def expensive_models(self) -> list[UUID]:
        """
        Models that cost more than an ordinary one: they spend people's
        expensive-model allowance.
        """
        return [model.id for model in self.enabled.values() if model.cost_weight > 1]

    def weight(self, llm_id: UUID) -> float:
        """How many times an ordinary model this one costs."""
        return self.all[llm_id].cost_weight

    def pick_one(
        self,
        models: list[UUID],
        excluded: list[UUID] = [],
        hard_excluded: Sequence[UUID] = (),
    ) -> UUID:
        """
        Randomly select a model from a list, excluding specified models.

        Args:
            models: List of available model names to choose from
            excluded: Models to leave out while others are left
            hard_excluded: Models never to pick, such as expensive ones once
                the person's allowance for them is spent

        Returns:
            UUID: Selected LLM id

        Raises:
            NoModelLeft: If the hard exclusions leave no model
        """
        if len(models) == 0:
            logger.critical("No model to choose from")
            # FIXME use Error that can be toasted
            raise Exception("No model available for this mode")

        allowed = [_id for _id in models if _id not in hard_excluded]
        if len(allowed) == 0:
            raise NoModelLeft()

        # Filter out excluded models
        models_pool = [_id for _id in allowed if _id not in excluded]

        logger.debug("chosing from:" + str(models_pool))
        logger.debug("excluded:" + str(excluded))

        # Handle empty pool
        if len(models_pool) == 0:
            # TODO: tell user in a toast notif that we couldn't respect prefs
            logger.warning("Couldn't respect exclusion prefs")
            # Fall back to the allowed models if couldn't respect exclusions
            models_pool = allowed

        # Random selection from available models
        picked_index = np.random.choice(len(models_pool), p=None)
        return models_pool[picked_index]

    def pick_two(
        self,
        mode: SelectionMode | None = "random",
        custom_selection: CustomModelsSelection = None,
        unavailable_models: list[UUID] = [],
        hard_excluded: Sequence[UUID] = (),
    ) -> tuple[UUID, UUID]:
        """
        Select two models based on the comparison mode.

        Supports multiple selection modes:
        - random: Two random models
        - big-vs-small: One large model vs one small model
        - small-models: Two small models
        - custom: User-specified models

        Args:
            mode: Selection mode string
            custom_models_selection: User's custom model choices (if custom mode)
            unavailable_models: Models that are currently unavailable/offline
            hard_excluded: Models never to pick, see `pick_one`

        Returns:
            tuple: (model_a_id, model_b_id) - pair of model ids, randomly swapped

        Raises:
            NoModelLeft: If the hard exclusions leave a side with no model, or
                the custom selection holds excluded models
        """
        import random

        # FIXME rework unavailable_models, models should be available if endpoint is defined or use class attribute to store unavailable models

        if mode == "big-vs-small":
            # Compare large models against small models
            model_a_id = self.pick_one(
                self.big_models, unavailable_models, hard_excluded
            )
            model_b_id = self.pick_one(
                self.small_models, unavailable_models, hard_excluded
            )

        elif mode == "small-models":
            # Compare two small models
            model_a_id = self.pick_one(
                self.small_models, unavailable_models, hard_excluded
            )
            model_b_id = self.pick_one(
                self.small_models, [*unavailable_models, model_a_id], hard_excluded
            )

        elif mode == "custom" and custom_selection and len(custom_selection) > 0:
            # `AddFirstTextBody` already refuses anything but one or two UUIDs,
            # but this is also called from the CLI, where nothing has checked.
            if len(custom_selection) > 2:
                raise ValueError("At most two models can be selected.")
            try:
                custom_selection = [UUID(llm_id) for llm_id in custom_selection]
            except ValueError:
                raise ValueError("Custom LLMs selection contains invalid ids")

            if unknown_llms := [
                llm_id
                for llm_id in custom_selection
                if llm_id not in self.random_models
            ]:
                logger.error(
                    f"`custom_models_selection` with unavailable LLM ids: {unknown_llms}"
                )
                raise ValueError(f"Custom LLMs selection contains unavailable LLMs")

            # Refused rather than swapped: the person named these models.
            if excluded_picks := [
                llm_id for llm_id in custom_selection if llm_id in hard_excluded
            ]:
                raise NoModelLeft(excluded_picks)

            if len(custom_selection) == 1:
                # One model chosen by user, pair with random model
                model_a_id = custom_selection[0]
                model_b_id = self.pick_one(
                    self.random_models,
                    [*unavailable_models, model_a_id],
                    hard_excluded,
                )
            elif len(custom_selection) == 2:
                # Two models chosen by user
                model_a_id = custom_selection[0]
                model_b_id = custom_selection[1]

        else:
            # Default to random mode
            model_a_id = self.pick_one(
                self.random_models, unavailable_models, hard_excluded
            )
            model_b_id = self.pick_one(
                self.random_models, [*unavailable_models, model_a_id], hard_excluded
            )

        # Randomly swap models to avoid position bias
        swap = random.randint(0, 1)
        if swap == 1:
            return (model_b_id, model_a_id)
        return (model_a_id, model_b_id)


@redis_cache(REDIS_LLMS_DATA_CACHE_KEY)
async def get_llms_data() -> LLMsData:
    """
    Load LLMs definitions from database.
    File contains metadata: params, pricing, reasoning capability, licenses, etc.
    """

    try:
        async with get_session() as session:
            llms = (await session.exec(select(LLMData))).all()
            return LLMsData.model_validate({"all": llms})
    except Exception as e:
        logger.error(f"[DB] Error loading LLMsData: {e}")
        raise


class LLMList(BaseModel):
    data_timestamp: float | None
    models: list[APILLMData]
    style_coefficients: dict[str, float] | None
    # How far a model's rank may move either way and still be shown, see
    # AppSettings.ranking_max_rank_spread.
    max_rank_spread: int
    currency: CurrencyInfo


# FIXME use cache?
async def get_llms_list() -> LLMList:
    llms = await get_llms_data()
    ranking = get_ranking()
    currency = await get_currency_info()
    app_settings = await get_app_settings()

    return LLMList.model_validate(
        {
            "models": llms.all.values(),
            "data_timestamp": ranking.timestamp if ranking else None,
            "style_coefficients": ranking.style_coefficients if ranking else None,
            "max_rank_spread": app_settings.ranking_max_rank_spread,
            "currency": currency,
        },
        context={"ranking": ranking},
    )


async def pick_replacement_model(
    comparison: "ComparisonRead", pos: "BotPos", expensive_available: bool = False
) -> str | None:
    """
    Pick a replacement model from the appropriate pool, excluding both current models.

    Only an expensive model may stand in for an expensive one, and only while
    the person's expensive allowance has room (`expensive_available`). A
    cheap side was charged at the cheap rate, and the person may have no
    expensive allowance left.
    """
    models = await get_llms_data()
    other_pos: "BotPos" = "b" if pos == "a" else "a"
    failing = getattr(comparison, f"llm_id_{pos}")
    other = getattr(comparison, f"llm_id_{other_pos}")
    excluded = [failing, other]

    # Pick from the right pool based on mode
    if comparison.mode == "small-models":
        pool = models.small_models
    elif comparison.mode == "big-vs-small":
        pool = (
            models.big_models if failing in models.big_models else models.small_models
        )
    else:
        pool = models.random_models

    expensive = models.expensive_models
    if failing not in expensive or not expensive_available:
        pool = [llm_id for llm_id in pool if llm_id not in expensive]

    try:
        return models.pick_one(pool, excluded=excluded)
    except Exception:
        return None
