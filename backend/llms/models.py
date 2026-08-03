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

from typing import Annotated, Any, Literal, Self, TypeVar, get_args

from pydantic import (
    AfterValidator,
    BaseModel,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from backend.llms.utils import convert_range_to_value, get_llm_impact
from utils.database.models.llms import LLMEndpoint, LLMLabPublic, LLMLicensePublic
from utils.database.models.llms.llm import LLMDataBase

# LLM scale classes
SizeClass = Literal["XS", "S", "M", "L", "XL"]
SIZE_CLASSES: tuple[SizeClass, ...] = get_args(SizeClass)
SIZE_CLASSES_SCALE: dict[SizeClass, int | float] = {
    # in billion params
    "XS": 15,
    "S": 60,
    "M": 100,
    "L": 400,
    "XL": float("inf"),
}

EnergyClass = Literal["A", "B", "C", "D", "E", "F"]
ENERGY_CLASSES: tuple[EnergyClass, ...] = get_args(EnergyClass)
ENERGY_CLASSES_SCALE: dict[EnergyClass, int | float] = {
    # in wh
    "A": 100,
    "B": 300,
    "C": 1_000,
    "D": 3_000,
    "E": 10_000,
    "F": float("inf"),
}

ClassT = TypeVar("ClassT", bound=SizeClass)


def get_class(scale: dict[ClassT, int | float], v: int | float) -> ClassT:
    for k, kv in scale.items():
        if v < kv:
            return k
    raise Exception("Error: Could not compute scale value")


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
        positive_prefs_ratio: Share of positive tags, null when the model has
            no tagged votes or the instance has turned off a whole side
        total_prefs: Total number of preference votes received
        counts: Count per vote tag key, including keys no longer offered
    """

    positive_prefs_ratio: float | None
    total_prefs: int
    counts: dict[str, int]

    @field_validator("positive_prefs_ratio", mode="before")
    @classmethod
    def handle_nan_ratio(cls, value: Any) -> float | None:
        """A ratio that cannot be computed is absent, not a number."""
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
        return value


class APILLMDataBase(LLMDataBase):
    """
    Base LLM class used for LLM picker and LLM list.
    """

    status: Literal["enabled", "archived"]
    license: LLMLicensePublic
    lab: LLMLabPublic

    @computed_field  # type: ignore[prop-decorator]
    @property
    def size_class(self) -> SizeClass:
        return get_class(SIZE_CLASSES_SCALE, self.params)

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

    @computed_field  # type: ignore[prop-decorator]
    @property
    def energy_class(self) -> EnergyClass:
        return get_class(ENERGY_CLASSES_SCALE, self.wh_per_million_token)


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


class APILLMData(APILLMDataBase):
    """
    LLM data used for LLM list, sent to clients.
    !Warning: make sure there's no secrets.
    """

    data: DatasetData | None = None
    prefs: PreferencesData | None = None

    @model_validator(mode="after")
    def inject_ranking_data(self, info: ValidationInfo) -> Self:
        if data := info.context.get("ranking"):
            self.data = data.rankings.get(str(self.id))
            self.prefs = data.preferences.get(str(self.id))

        return self
