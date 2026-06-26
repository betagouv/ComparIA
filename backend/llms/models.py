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
    BaseModel,
    ConfigDict,
    computed_field,
    field_validator,
)

# Type definitions for model categorization
FriendlySize = Literal["XS", "S", "M", "L", "XL"]  # Human-readable size categories
Distribution = Literal[
    "api-only", "open-weights", "fully-open-source"
]  # License/access types
FRIENDLY_SIZE: tuple[FriendlySize, ...] = get_args(FriendlySize)


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
    api_version: str | None = None
    api_model_id: str


# Type alias: rounds floats to nearest integer
RoundInt = Annotated[int | float, AfterValidator(lambda n: round(n))]


# TODO could be moved to 'utils/ranking'
class RankingVariant(BaseModel):
    """
    A single Bradley-Terry ranking view (one set of Elo scores and ranks).

    The leaderboard ships two of these per model: the style-controlled view
    (shown by default) and the plain view used when the user turns Style Control
    off. They share the raw vote count but differ in Elo, ranks and win
    probabilities once presentation features are regressed out.

    Attributes:
        elo: Estimated Elo rating (median/central estimate)
        score_p2_5/p97_5: Confidence interval bounds (2.5th and 97.5th percentile)
        rank/rank_p2_5/rank_p97_5: Model ranking with confidence bounds
        n_match: Number of comparisons in dataset
        mean_win_prob: Probability model wins in random matchup
        win_rate: Percentage of matches won
        trust_range: Computed confidence interval for ranking
    """

    elo: RoundInt
    score_p2_5: RoundInt
    score_p97_5: RoundInt
    rank_p2_5: int
    rank_p97_5: int
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


# TODO could be moved to 'utils/ranking'
class DatasetData(RankingVariant):
    """
    Ranking/evaluation data exposed for a model.

    The top-level fields are the style-controlled ranking (Style Control on,
    the default). ``uncontrolled`` carries the plain Bradley-Terry ranking the
    frontend swaps in when Style Control is toggled off, so the leaderboard can
    switch views without a recompute. It is ``None`` for models that are
    degenerate (never won or never lost) in the plain fit.
    """

    uncontrolled: RankingVariant | None = None


# TODO could be moved to 'utils/ranking'
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


class LLMDataBase(BaseModel):
    """
    Individual LLM base model definition (before enrichment).

    See `utils/models/llms.py`.

    !Warning: Make sure to reflect changes to `LLMDataRawBase`
    """

    new: bool
    status: Literal["archived", "missing_data", "disabled", "enabled"]
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
    specific_portals: list[str] | None


class LLMDataEnhanced(BaseModel):
    """
    Individual LLM enhanced model definition (after enrichment from Organisation).

    See `utils/models/llms.py`.

    !Warning: Make sure to reflect changes to `LLMDataRaw`
    """

    # Merged from License
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None
    # Merged from Organisation
    organisation: str
    icon_path: str


class LLMData(LLMDataBase, LLMDataEnhanced):
    """
    Final individual LLM model definition.

    Populated with 'utils/models/generated-models.json' data.
    It is immutable and no default values are defined so it expects complete data.
    See `utils/models/llms.py`.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    status: Literal["archived", "enabled"]
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
            The system prompt is included in the Comparison when provided.
            This ensures consistent behavior across multiple comparisons.
        """
        return None


class LLMDataArchived(LLMData):
    status: Literal["archived"]


class LLMDataEnabled(LLMData):
    """
    Enabled LLM for proper typing with required Endpoint
    """

    status: Literal["enabled"]
    endpoint: Endpoint
