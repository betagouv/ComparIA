"""
Data validation models using Pydantic.

Defines all data structures for:
- Model metadata (licenses, architectures, model definitions)
- Ranking/preference data (Elo scores, preference statistics)
- Conversation data (messages, participant info, metadata)

Uses Pydantic validators to ensure data integrity:
- Architecture validation (must exist in archs.json)
- License validation (must be defined in licenses.json)
- Model status consistency
- Required fields for enabled models

The models are organized in hierarchy:
- RawModel/Model: Individual model definitions
- RawOrganisation/Organisation: Organization containing multiple models
- Conversation/ConversationMessage: Chat history with metadata
- DatasetData/PreferencesData: Rankings and user preferences
"""

import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, get_args

from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    RootModel,
    ValidationError,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from backend.models.utils import convert_range_to_value, get_llm_impact

ROOT_PATH = Path(__file__).parent.parent
FRONTEND_PATH = ROOT_PATH / "frontend"

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

    elo: RoundInt = Field(validation_alias="median")
    score_p2_5: RoundInt = Field(validation_alias="p2.5")
    score_p97_5: RoundInt = Field(validation_alias="p97.5")
    rank_p2_5: int = Field(validation_alias="rank_p2.5")
    rank_p97_5: int = Field(validation_alias="rank_p97.5")
    rank: int
    n_match: int
    mean_win_prob: float
    win_rate: float

    @computed_field
    @property
    def trust_range(self) -> list[int, int]:
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
        cls, value: str, info: ValidationInfo
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

    @computed_field
    @property
    def friendly_size(self) -> FriendlySize:
        intervals = [(0, 15), (15, 60), (60, 100), (100, 400), (400, float("inf"))]

        for i, (lower, upper) in enumerate(intervals):
            if lower <= self.params < upper:
                return FRIENDLY_SIZE[i]

        raise Exception("Error: Could not guess friendly_size")

    @computed_field
    @property
    def required_ram(self) -> int | float:
        if self.quantization == "q8":
            return self.params * 2

        # We suppose from q4 to fp16
        return self.params

    @computed_field
    @property
    def wh_per_million_token(self) -> int | float:
        model_info = {
            "params": self.params,
            "active_params": self.active_params,
            "quantization": self.quantization,
        }
        impact = get_llm_impact(
            model_info,
            self.id,
            1_000_000,
            None,
        )

        if impact and hasattr(impact, "energy") and hasattr(impact.energy, "value"):
            energy_kwh = convert_range_to_value(impact.energy.value)
            return energy_kwh * 1000

        # FIXME return None?
        return 0


# Model to validate organisations data from 'utils/models/models.json'
class RawOrganisation(BaseModel):
    name: str
    icon_path: str | None = None  # FIXME required?
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[RawModel]

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


class ConversationMessage(BaseModel):
    """
    Single message in a conversation.

    Represents one user or assistant message with content and metadata.
    Assistant messages MUST include output_tokens for tracking.

    Attributes:
        role: "user", "assistant", or "system"
        content: Message text content
        metadata: Additional data (output_tokens for assistant messages, etc.)
    """

    role: str
    content: str
    metadata: dict[str, Any] | None = None

    # Validate that assistant messages include token counts
    @model_validator(mode="after")
    def check_assistant_metadata(self) -> "ConversationMessage":
        if self.role == "assistant":
            if not self.metadata or "output_tokens" not in self.metadata:
                raise ValueError(
                    "Assistant messages must have 'output_tokens' in metadata"
                )
        return self


# Type alias for list of messages
ConversationMessages = RootModel[list[ConversationMessage]]


class Conversation(BaseModel):
    """
    Complete conversation record with both models' responses and metadata.

    Stores a paired comparison between two models on the same prompts.
    Used to persist conversation data to database and JSON logs.

    Attributes:
        id: Internal database ID
        timestamp: When conversation was created
        model_a_name/model_b_name: Model identifiers
        conversation_a/conversation_b: Message histories for each model
        conv_turns: Number of user-model exchange rounds
        system_prompt_a/b: System prompts used (if any)
        conversation_pair_id: Unique ID combining both conv IDs
        conv_a_id/conv_b_id: Individual conversation IDs
        session_hash: User session identifier
        visitor_id: Matomo visitor tracking ID (if enabled)
        ip: User's IP address (PII)
        model_pair_name: Sorted model pair for analysis
        opening_msg: Initial user prompt
        archived: Whether conversation is archived
        mode: Model selection mode (random, big-vs-small, etc.)
        custom_models_selection: Custom model selection if mode=custom
        short_summary: Auto-generated summary (added during post-processing)
        keywords/categories/languages: Extracted metadata (post-processing)
        pii_analyzed/contains_pii: PII detection results
        total_conv_a_output_tokens/total_conv_b_output_tokens: Token usage
        ip_map: Geographic region derived from IP
        postprocess_failed: Whether post-processing failed
    """

    id: int
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    model_a_name: str
    model_b_name: str
    conversation_a: ConversationMessages
    conversation_b: ConversationMessages
    conv_turns: int = 0
    system_prompt_a: str | None = None
    system_prompt_b: str | None = None
    conversation_pair_id: str
    conv_a_id: str
    conv_b_id: str
    session_hash: str
    visitor_id: str | None = None
    ip: str | None = None  # Warning: PII
    model_pair_name: str
    opening_msg: str
    archived: bool = False
    mode: str | None = None
    custom_models_selection: dict[str, Any] | None = None
    short_summary: str | None = None
    keywords: dict[str, Any] | None = None
    categories: dict[str, Any] | None = None
    languages: dict[str, Any] | None = None
    pii_analyzed: bool = False
    contains_pii: bool | None = None
    total_conv_a_output_tokens: int | None = None
    total_conv_b_output_tokens: int | None = None
    ip_map: str | None = None
    postprocess_failed: bool = False


class CohortRequest(BaseModel):
    session_hash: str
    cohorts: str


class FrontendLogEntry(BaseModel):
    """
    Single log entry from frontend (simplified format).

    Fields:
        level: Log level (info, warn, error, debug)
        message: Log message text
    """
    level: str
    message: str


class FrontendLogRequest(BaseModel):
    """
    Single frontend log sent to backend (simplified format).

    Fields:
        level: Log level (info, warn, error, debug)
        message: Log message text
        session_hash: User session identifier
        user_agent: Browser user agent string
    """
    level: str
    message: str
    session_hash: str | None = None
    user_agent: str | None = None