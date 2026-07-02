import logging
from typing import TYPE_CHECKING, Annotated, Any
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
from backend.llms.models import APILLMData, LLMDataArchived, LLMDataEnabled
from backend.utils.countries import get_ranking
from utils.database.models.llms import LLMData
from utils.database.session import get_session
from utils.storage.redis import REDIS_LLMS_DATA_CACHE_KEY, redis_cache

if TYPE_CHECKING:
    from utils.database.models import BotPos, ComparisonRead

logger = logging.getLogger("languia")


class LLMsData(BaseModel):
    all: dict[
        UUID,
        Annotated[LLMDataEnabled | LLMDataArchived, Field(discriminator="status")],
    ]

    @field_validator("all", mode="before")
    @classmethod
    def filter_disabled(cls, llms: Any) -> dict[str, Any]:
        """
        Filter out disabled LLMs.
        """
        return {
            llm.id: llm
            for llm in llms
            if (
                llm.status == "enabled"
                and llm.endpoint is not None
                and llm.endpoint.api_key is not None
            )
            or llm.status == "archived"
        }

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
    def pricey_models(self) -> list[UUID]:
        """
        Commercial models with higher API costs (e.g., Claude, GPT-4)
        These have stricter rate limits applied
        """
        return [model.id for model in self.enabled.values() if model.rate_limited]

    def pick_one(self, models: list[UUID], excluded: list[UUID] = []) -> UUID:
        """
        Randomly select a model from a list, excluding specified models.

        Args:
            models: List of available model names to choose from
            excluded: List of model names to exclude from selection

        Returns:
            UUID: Selected LLM id

        Raises:
            Error: If no models are available after filtering
        """
        # Filter out excluded models
        models_pool = [_id for _id in models if _id not in excluded]

        logger.debug("chosing from:" + str(models_pool))
        logger.debug("excluded:" + str(excluded))

        # Handle empty pool
        if len(models_pool) == 0:
            # TODO: tell user in a toast notif that we couldn't respect prefs
            logger.warning("Couldn't respect exclusion prefs")
            if len(models) == 0:
                logger.critical("No model to choose from")
                # No models available at all
                # FIXME use Error that can be toasted
                # raise Exception(
                #     duration=0,
                #     message="Le comparateur a un problème et aucun des modèles parmi les sélectionnés n'est disponible, veuillez réessayer un autre mode ou revenir plus tard.",
                # )
                raise Exception(
                    "Le comparateur a un problème et aucun des modèles parmi les sélectionnés n'est disponible, veuillez réessayer un autre mode ou revenir plus tard.",
                )
            else:
                # Fall back to all models if couldn't respect exclusions
                # FIXME hmm readding excluded models ?
                models_pool = models

        # Random selection from available models
        picked_index = np.random.choice(len(models_pool), p=None)
        return models_pool[picked_index]

    def pick_two(
        self,
        mode: SelectionMode | None = "random",
        custom_selection: CustomModelsSelection = None,
        unavailable_models: list[UUID] = [],
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

        Returns:
            tuple: (model_a_id, model_b_id) - pair of model ids, randomly swapped
        """
        import random

        # FIXME rework unavailable_models, models should be available if endpoint is defined or use class attribute to store unavailable models

        if mode == "big-vs-small":
            # Compare large models against small models
            model_a_id = self.pick_one(self.big_models, excluded=unavailable_models)
            model_b_id = self.pick_one(self.small_models, excluded=unavailable_models)

        elif mode == "small-models":
            # Compare two small models
            model_a_id = self.pick_one(self.small_models, excluded=unavailable_models)
            model_b_id = self.pick_one(
                self.small_models, excluded=[*unavailable_models, model_a_id]
            )

        elif mode == "custom" and custom_selection and len(custom_selection) > 0:
            if unknown_llms := [
                llm_id
                for llm_id in custom_selection
                if llm_id not in self.random_models
            ]:
                logger.error(
                    f"`custom_models_selection` with unavailable LLM ids: {unknown_llms}"
                )
                raise ValueError(f"Custom LLMs selection contains unavailable LLMs")

            if len(custom_selection) == 1:
                # One model chosen by user, pair with random model
                model_a_id = custom_selection[0]
                model_b_id = self.pick_one(
                    self.random_models, excluded=[*unavailable_models, model_a_id]
                )
            elif len(custom_selection) == 2:
                # Two models chosen by user
                model_a_id = custom_selection[0]
                model_b_id = custom_selection[1]

        else:
            # Default to random mode
            model_a_id = self.pick_one(self.random_models, excluded=unavailable_models)
            model_b_id = self.pick_one(
                self.random_models, excluded=[*unavailable_models, model_a_id]
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


# FIXME use cache?
async def get_llms_list() -> LLMList:
    llms = await get_llms_data()
    ranking = get_ranking()

    return LLMList.model_validate(
        {
            "models": llms.all.values(),
            "data_timestamp": ranking.timestamp if ranking else None,
            "style_coefficients": ranking.style_coefficients if ranking else None,
        },
        context={"ranking": ranking},
    )


async def pick_replacement_model(
    comparison: "ComparisonRead", pos: "BotPos"
) -> str | None:
    """Pick a replacement model from the appropriate pool, excluding both current models."""
    models = await get_llms_data()
    other_pos: BotPos = "b" if pos == "a" else "a"
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

    try:
        return models.pick_one(pool, excluded=excluded)
    except Exception:
        return None
