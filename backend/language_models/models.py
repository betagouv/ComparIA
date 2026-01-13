"""
Data validation models using Pydantic.

Defines all data structures for:
- Model metadata (licenses, architectures, model definitions)
- Ranking/preference data (Elo scores, preference statistics)

Uses Pydantic validators to ensure data integrity:
- Architecture validation (must exist in archs.json)
- License validation (must be defined in licenses.json)
- Model status consistency
- Required fields for enabled models

The models are organized in hierarchy:
- RawModel/Model: Individual model definitions
- RawOrganisation/Organisation: Organization containing multiple models
- DatasetData/PreferencesData: Rankings and user preferences
"""

from typing import Annotated, Any, Literal, get_args

from pydantic import (
    AfterValidator,
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from backend.config import FRONTEND_PATH, ROOT_PATH
from backend.language_models.utils import convert_range_to_value, get_llm_impact

# Type definitions for model categorization
FriendlySize = Literal["XS", "S", "M", "L", "XL"]  # Human-readable size categories
Distribution = Literal[
    "api-only", "open-weights", "fully-open-source"
]  # License/access types
FRIENDLY_SIZE: tuple[FriendlySize, ...] = get_args(FriendlySize)


# License definitions for models
class License(BaseModel):
    """
    License metadata for a model.

    Defines licensing terms, distribution restrictions, and permitted uses.
    Used to validate 'utils/models/licenses.json'.

    Attributes:
        license: License identifier (e.g., "apache-2.0", "mit", "proprietary")
        license_desc: Human-readable description of the license
        distribution: How model is distributed (api-only, open-weights, fully-open-source)
        reuse: Whether model can be reused/redistributed
        commercial_use: Whether commercial use is permitted (None = unknown)
        reuse_specificities: Additional reuse restrictions/notes
        commercial_use_specificities: Additional commercial use restrictions/notes
    """

    license: str
    license_desc: str
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


# Model architecture definitions
class Arch(BaseModel):
    """
    Model architecture information.

    Defines neural network architecture and properties.
    Used to validate 'utils/models/archs.json'.

    Attributes:
        id: Architecture identifier (e.g., "transformer", "moe")
        name: Short name
        title: Display title
        desc: Detailed description of the architecture
    """

    id: str
    name: str
    title: str
    desc: str


class Endpoint(BaseModel):
    """
    API endpoint configuration for model access.

    Specifies how to reach a model's API (OpenAI-compatible, custom, etc).

    Attributes:
        api_type: API format (default "openai" for OpenAI-compatible APIs)
        api_base: Base URL for the API endpoint
        api_model_id: Model identifier used in API calls
    """

    api_type: str | None = "openai"
    api_base: str | None = None
    api_model_id: str


# Type alias: rounds floats to nearest integer
RoundInt = Annotated[int | float, AfterValidator(lambda n: round(n))]


class DatasetData(BaseModel):
    """
    Ranking/evaluation data from benchmark datasets.

    Contains Elo ratings and confidence intervals from model comparison datasets
    (e.g., LMSYS arena, ComparIA own data).

    Attributes:
        elo: Estimated Elo rating (median/central estimate)
        score_p2_5/p97_5: Confidence interval bounds (2.5th and 97.5th percentile)
        rank/rank_p2_5/rank_p97_5: Model ranking with confidence bounds
        n_match: Number of comparisons in dataset
        mean_win_prob: Probability model wins in random matchup
        win_rate: Percentage of matches won
        trust_range: Computed confidence interval for ranking
    """

    elo: RoundInt = Field(validation_alias=AliasChoices("median", "elo"))
    score_p2_5: RoundInt = Field(validation_alias=AliasChoices("p2.5", "score_p2_5"))
    score_p97_5: RoundInt = Field(validation_alias=AliasChoices("p97.5", "score_p97_5"))
    rank_p2_5: int = Field(validation_alias=AliasChoices("rank_p2.5", "rank_p2_5"))
    rank_p97_5: int = Field(validation_alias=AliasChoices("rank_p97.5", "rank_p97_5"))
    rank: int
    n_match: int
    mean_win_prob: float
    win_rate: float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def trust_range(self) -> list[int]:
        """Confidence interval: [lower bound, upper bound] for ranking."""
        return [
            self.rank - self.rank_p2_5,
            self.rank_p97_5 - self.rank,
        ]


class PreferencesData(BaseModel):
    """
    User preference statistics from ComparIA voting.

    Aggregated counts of user ratings for specific quality attributes.

    Attributes:
        positive_prefs_ratio: Percentage of positive preferences (useful, complete, etc.)
        total_prefs: Total number of preference votes received
        useful/complete/creative/clear_formatting: Count of positive preferences
        incorrect/superficial/instructions_not_followed: Count of negative preferences
    """

    positive_prefs_ratio: float
    total_prefs: int
    # Positive quality indicators
    useful: int
    clear_formatting: int
    complete: int
    creative: int
    # Negative quality indicators
    incorrect: int
    instructions_not_followed: int
    superficial: int

    @field_validator("positive_prefs_ratio", mode="before")
    @classmethod
    def handle_nan_ratio(cls, value: Any) -> float:
        """Replace NaN values with -1 to prevent JSON serialization errors."""
        import math

        if isinstance(value, float) and math.isnan(value):
            return -1
        return value


# Raw model definitions from 'utils/models/models.json'
class RawModel(BaseModel):
    """
    Individual LLM model definition (before enrichment).

    Raw model data loaded from 'utils/models/models.json'.
    Contains basic model information (name, params, licensing).
    Gets enriched with license data, architecture info, and rankings to become Model class.

    Attributes:
        new: Whether this is a newly added model
        status: Model status (archived, missing_data, disabled, enabled)
        id: Unique model identifier (e.g., "openai/gpt-4")
        simple_name: Human-readable model name
        license: License identifier (maps to License class)
        fully_open_source: Whether model weights are fully open/public
        release_date: Model release date in MM/YYYY format
        arch: Model architecture (transformer, moe, etc. - maps to Arch class)
        params: Total parameters in billions
        active_params: Active parameters (only for MoE models)
        reasoning: Extended thinking capability (False, True, or "hybrid")
        quantization: Quantization scheme applied (q4, q8, or None for full precision)
        url: Model homepage or documentation URL
        endpoint: API access configuration (None for unavailable models)
        desc: Detailed model description
        size_desc: Human-readable size category (e.g., "Small but Mighty")
        fyi: Additional notes for users
        pricey: Whether model has high API costs (triggers stricter rate limits)
    """

    new: bool = False
    status: Literal["archived", "missing_data", "disabled", "enabled"] | None = (
        "enabled"
    )
    id: str
    simple_name: str
    license: str
    fully_open_source: bool = False
    release_date: str = Field(pattern=r"^[0-9]{02}/[0-9]{4}$")
    arch: str
    params: int | float
    active_params: int | float | None = Field(default=None, validate_default=True)
    reasoning: bool | Literal["hybrid"] = False
    quantization: Literal["q4", "q8"] | None = None
    url: str | None = None
    endpoint: Endpoint | None = None
    desc: str
    size_desc: str
    fyi: str
    pricey: bool = False

    @field_validator("arch", mode="after")
    @classmethod
    def check_arch_exists(cls, value: str, info: ValidationInfo) -> str:
        assert info.context is not None
        assert info.context["archs"] is not None

        if value.replace("maybe-", "") not in info.context["archs"]:
            raise PydanticCustomError(
                "missing_arch", f"Missing arch '{value}' infos in 'archs.json'."
            )

        if info.data["license"] != "proprietary" and "maybe" in value:
            raise PydanticCustomError(
                "wrong_arch",
                f"Arch should not be 'maybe' since license is not 'proprietary'.",
            )

        return value

    @field_validator("active_params", mode="before")
    @classmethod
    def check_active_params_is_defined_if_moe(
        cls, value: int | float | None, info: ValidationInfo
    ) -> int | float | None:
        if "arch" in info.data and "moe" in info.data["arch"] and value is None:
            raise PydanticCustomError(
                "missing_active_params",
                f"Model's arch is '{info.data['arch']}' and requires 'active_params' to be defined.",
            )

        return value

    @model_validator(mode="after")
    def check_endpoint(self):
        if self.status == "enabled" and not self.endpoint:
            raise PydanticCustomError(
                "endpoint", "Model is enabled but no endpoint has been found."
            )
        return self


# Enriched model definition generated from RawModel + licenses + rankings + preferences
class Model(RawModel):
    """
    Complete model definition with enriched metadata.

    Inherits from RawModel and adds:
    - License data (distribution, reuse rights)
    - Organisation/vendor information
    - Ranking data (Elo, confidence intervals)
    - User preference statistics
    - Computed fields (friendly size, RAM requirements, energy impact)

    Generated by build_models.py from 'utils/models/models.json' and saved as
    'utils/models/generated-models.json'.

    Computed Properties:
        friendly_size: Human-readable category (XS, S, M, L, XL) based on params
        required_ram: Estimated RAM needed to run model (depends on quantization)
        wh_per_million_token: Energy consumption per million tokens
    """

    status: Literal["archived", "enabled", "disabled"] = "enabled"
    # Merged from License
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None = None
    # Merged from Organisation
    organisation: str
    icon_path: str | None = None  # FIXME required?
    # Merged from extra-data
    data: DatasetData | None = None
    prefs: PreferencesData | None = None

    @field_validator("distribution", mode="before")
    @classmethod
    def check_distribution(
        cls, value: Distribution, info: ValidationInfo
    ) -> Distribution:
        if info.data["fully_open_source"]:
            value = "fully-open-source"

        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def friendly_size(self) -> FriendlySize:
        intervals = [(0, 15), (15, 60), (60, 100), (100, 400), (400, float("inf"))]

        for i, (lower, upper) in enumerate(intervals):
            if lower <= self.params < upper:
                return FRIENDLY_SIZE[i]

        raise Exception("Error: Could not guess friendly_size")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def required_ram(self) -> int | float:
        if self.quantization == "q8":
            return self.params * 2

        # We suppose from q4 to fp16
        return self.params

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wh_per_million_token(self) -> int | float:
        impact = get_llm_impact(self, 1_000_000, None)

        if impact:
            energy_kwh = convert_range_to_value(impact.energy.value)
            return energy_kwh * 1000

        # FIXME return None?
        return 0


class LanguageModel(BaseModel):
    """
    Final language model definition.

    Populated with 'utils/models/generated-models.json' data.
    It is immutable and no default values are defined so it expects complete data.
    """

    model_config = ConfigDict(frozen=True)

    new: bool
    status: Literal["archived", "enabled"]
    id: str
    simple_name: str
    license: str
    fully_open_source: bool
    release_date: str
    arch: str
    params: int | float
    active_params: int | float | None
    reasoning: bool | Literal["hybrid"]
    quantization: Literal["q4", "q8"] | None
    url: str | None
    endpoint: Endpoint | None
    pricey: bool
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None
    organisation: str
    icon_path: str
    data: DatasetData | None
    prefs: PreferencesData | None
    friendly_size: FriendlySize
    required_ram: int | float
    wh_per_million_token: int | float

    @computed_field  # type: ignore[prop-decorator]
    @property
    def system_prompt(self) -> str | None:
        """
        Get model-specific system prompt if configured.

        Allows customization of model behavior through system prompts.
        Currently only specific French models (chocolatine, lfm-40b) have custom prompts.
        Other models use None (no system prompt by default).

        Args:
            model_name: Model identifier (e.g., "openai/gpt-4", "chocolatine")

        Returns:
            str: French system prompt, or None for no custom system prompt

        Note:
            The system prompt is included in conversations when provided.
            This ensures consistent behavior across multiple conversations.
        """
        return None


# Model to validate organisations data from 'utils/models/models.json'
class RawOrganisation(BaseModel):
    name: str
    icon_path: str | None = None  # FIXME required?
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[RawModel] | list[Model]

    @field_validator("icon_path", mode="after")
    @classmethod
    def check_icon_exists(cls, value: str) -> str:
        file_path = FRONTEND_PATH / "static" / "orgs" / "ai" / value
        if "." in value and not file_path.exists():
            raise PydanticCustomError(
                "file_missing",
                f"'icon_path' is defined but the file '{file_path.relative_to(ROOT_PATH)}' doesn't exists.",
            )

        return value


# Model used to generated 'utils/models/generated-models.json'
class Organisation(RawOrganisation):
    models: list[Model]

    @field_validator("models", mode="before")
    @classmethod
    def enhance_models(cls, value: Any, info: ValidationInfo) -> list[RawModel]:
        assert info.context is not None
        assert info.context["data"] is not None
        assert info.context["licenses"] is not None

        for model in value:
            # forward organisation data
            model["organisation"] = info.data.get("name")
            model["icon_path"] = info.data.get("icon_path")

            # forward/inject license data
            if model["license"] not in info.context["licenses"]:
                raise PydanticCustomError(
                    "license_missing",
                    f"license is defined but license data is missing in 'licenses.json' for license '{model["license"]}'",
                )

            for k, v in info.context["licenses"][model["license"]].items():
                model[k] = v

            if model["license"] == "proprietary":
                model["reuse"] = info.data["proprietary_reuse"]
                model["commercial_use"] = info.data["proprietary_commercial_use"]

            # inject ranking/prefs data
            data = info.context["data"].get(model["id"])

            if data:
                model["data"] = data

                PREFS_KEYS = list(PreferencesData.model_fields.keys())
                prefs = {key: data.pop(key) for key in PREFS_KEYS}
                if prefs:
                    model["prefs"] = prefs

        return value


Licenses = RootModel[list[License]]
Archs = RootModel[list[Arch]]
RawOrgas = RootModel[list[RawOrganisation]]
Orgas = RootModel[list[Organisation]]
