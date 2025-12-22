import json
import logging
from functools import lru_cache
from typing import Any

import json5
import numpy as np
from pydantic import BaseModel, computed_field, field_validator

from backend.config import (
    BIG_MODELS_BUCKET_LOWER_LIMIT,
    MODELS_DATA_PATH,
    SMALL_MODELS_BUCKET_UPPER_LIMIT,
)
from backend.models.models import LanguageModel

logger = logging.getLogger("languia")


class LanguageModels(BaseModel):
    data_timestamp: float
    all: dict[str, LanguageModel]

    @field_validator("all", mode="before")
    @classmethod
    def filter_disabled(cls, values: Any) -> dict[str, Any]:
        return {
            _id: model for _id, model in values.items() if model["status"] != "disabled"
        }

    @computed_field  # type: ignore[prop-decorator]
    @property
    def enabled(self) -> dict[str, LanguageModel]:
        """
        Filter to only enabled models (removes disabled or deprecated models)
        """
        return {
            model.id: model
            for model in self.all.values()
            if model.status == "enabled" and model.endpoint
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


@lru_cache
def get_models() -> LanguageModels:
    """
    Load model definitions from generated configuration.
    File contains metadata: params, pricing, reasoning capability, licenses, etc.
    """
    data = json.loads(MODELS_DATA_PATH.read_text())

    return LanguageModels(data_timestamp=data["timestamp"], all=data["models"])
