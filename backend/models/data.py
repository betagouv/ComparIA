import json
from functools import lru_cache
from typing import Any

import json5
from pydantic import BaseModel, computed_field, field_validator

from backend.config import (
    BIG_MODELS_BUCKET_LOWER_LIMIT,
    MODELS_DATA_PATH,
    SMALL_MODELS_BUCKET_UPPER_LIMIT,
)
from backend.models.models import LanguageModel


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


@lru_cache
def get_models() -> LanguageModels:
    """
    Load model definitions from generated configuration.
    File contains metadata: params, pricing, reasoning capability, licenses, etc.
    """
    data = json.loads(MODELS_DATA_PATH.read_text())

    return LanguageModels(data_timestamp=data["timestamp"], all=data["models"])
