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

from pydantic import AfterValidator, BaseModel, computed_field, field_validator

from backend.llms.utils import convert_range_to_value, get_llm_impact
from utils.database.models.llms import LLMEndpoint, LLMLabPublic, LLMLicensePublic
from utils.database.models.llms.llm import LLMDataBase

# Type definitions for model categorization
FriendlySize = Literal["XS", "S", "M", "L", "XL"]  # Human-readable size categories
Distribution = Literal[
    "api-only", "open-weights", "fully-open-source"
]  # License/access types
FRIENDLY_SIZE: tuple[FriendlySize, ...] = get_args(FriendlySize)


class LitellmEndpoint(BaseModel):
    """
    Litellm API endpoint configuration for LLM access.

    Specifies how to reach a model's API (OpenAI-compatible, custom, etc).
    Computed from LLMDataEnabled

    Attributes:
        model: Model identifier used in API calls
        api_key: API secret key
        base_url: Base URL for the API endpoint (optional)
        api_verson: API version (optional)
    """

    model: str
    api_key: str
    base_url: str | None
    api_version: str | None


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


class APILLMDataBase(LLMDataBase):
    status: Literal["enabled", "archived"]
    license: LLMLicensePublic
    lab: LLMLabPublic

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
        energy_kwh = convert_range_to_value(impact.energy.value)

        return energy_kwh * 1000


class LLMDataArchived(APILLMDataBase):
    status: Literal["archived"]


class LLMDataEnabled(APILLMDataBase):
    """
    Enabled LLM for proper typing with required Endpoint
    """

    status: Literal["enabled"]
    api_model_id: str
    endpoint: LLMEndpoint

    @computed_field  # type: ignore[prop-decorator]
    @property
    def litellm_endpoint(self) -> LitellmEndpoint:
        """
        Litellm API endpoint args.
        """
        return LitellmEndpoint(
            api_version=self.endpoint.api_version,
            base_url=self.endpoint.api_base,
            api_key=self.endpoint.api_key,
            model=f"{self.endpoint.api_type}/{self.api_model_id}",
        )
