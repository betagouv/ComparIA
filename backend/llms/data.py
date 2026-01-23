import json
import logging
from functools import lru_cache
from typing import Annotated, Any

import numpy as np
from pydantic import BaseModel, Field, computed_field, field_validator

from backend.config import (
    BIG_MODELS_BUCKET_LOWER_LIMIT,
    MODELS_DATA_PATH,
    SMALL_MODELS_BUCKET_UPPER_LIMIT,
    CustomModelsSelection,
    SelectionMode,
)
from backend.llms.models import LanguageModeArchived, LanguageModelEnabled

logger = logging.getLogger("languia")


class LanguageModels(BaseModel):
    data_timestamp: float
    all: dict[
        str,
        Annotated[
            LanguageModelEnabled | LanguageModeArchived,
            Field(discriminator="status"),
        ],
    ]

    @field_validator("all", mode="before")
    @classmethod
    def filter_disabled(cls, values: Any) -> dict[str, Any]:
        return {
            _id: model for _id, model in values.items() if model["status"] != "disabled"
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def enabled(self) -> dict[str, LanguageModelEnabled]:
        """
        Filter to only enabled models (removes disabled or deprecated models)
        """
        return {
            model.id: model
            for model in self.all.values()
            if isinstance(model, LanguageModelEnabled)
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def random_models(self) -> list[str]:
        """
        All models (for standard random selection)
        """
        return [model.id for model in self.enabled.values()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def small_models(self) -> list[str]:
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
    def big_models(self) -> list[str]:
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
    def pricey_models(self) -> list[str]:
        """
        Commercial models with higher API costs (e.g., Claude, GPT-4)
        These have stricter rate limits applied
        """
        return [model.id for model in self.enabled.values() if model.pricey]

    def pick_one(self, models: list[str], excluded: list[str] = []) -> str:
        """
        Randomly select a model from a list, excluding specified models.

        Args:
            models: List of available model names to choose from
            excluded: List of model names to exclude from selection

        Returns:
            str: Selected model name

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
        unavailable_models: list[str] = [],
    ) -> tuple[str, str]:
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
            # User-selected models
            # FIXME: input sanitization needed
            # if any(mode[1], not in models):
            #     raise Exception(f"Model choice from value {str(model_dropdown_scoped)} not among possibilities")

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


@lru_cache
def get_models() -> LanguageModels:
    """
    Load model definitions from generated configuration.
    File contains metadata: params, pricing, reasoning capability, licenses, etc.
    """
    data = json.loads(MODELS_DATA_PATH.read_text())

    return LanguageModels(data_timestamp=data["timestamp"], all=data["models"])
