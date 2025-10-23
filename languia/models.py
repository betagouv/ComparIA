import datetime
from pathlib import Path
from pydantic import (
    AfterValidator,
    BaseModel,
    Field,
    RootModel,
    ValidationError,
    ValidationInfo,
    model_validator,
    computed_field,
    field_validator,
)
from pydantic_core import PydanticCustomError
from typing import Annotated, Any, Literal, get_args
from languia.reveal import get_llm_impact, convert_range_to_value

ROOT_PATH = Path(__file__).parent.parent
FRONTEND_PATH = ROOT_PATH / "frontend"

FriendlySize = Literal["XS", "S", "M", "L", "XL"]
Distribution = Literal["api-only", "open-weights", "fully-open-source"]
FRIENDLY_SIZE: tuple[FriendlySize, ...] = get_args(FriendlySize)


# Used to validate 'utils/models/licenses.json'
class License(BaseModel):
    license: str
    license_desc: str
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


# Used to validate 'utils/models/archs.json'
class Arch(BaseModel):
    id: str
    name: str
    title: str
    desc: str


class Endpoint(BaseModel):
    api_type: str | None = "openai"
    api_base: str | None = None
    api_model_id: str


class DatasetData(BaseModel):
    elo: Annotated[int | float, AfterValidator(lambda elo: round(elo))] = Field(
        validation_alias="median"
    )
    n_match: int
    mean_win_prob: float
    win_rate: float | None

    rank_p2_5: int = Field(validation_alias="rank_p2.5", exclude=True)
    rank_p97_5: int = Field(validation_alias="rank_p97.5", exclude=True)
    rank: int

    @computed_field
    @property
    def trust_range(self) -> list[int, int]:
        return [
            self.rank - self.rank_p2_5,
            self.rank_p97_5 - self.rank,
        ]


class PreferencesData(BaseModel):
    positive_prefs_ratio: float
    total_prefs: int
    # Positive count
    useful: int
    clear_formatting: int
    complete: int
    creative: int
    # Negative count
    incorrect: int
    instructions_not_followed: int
    superficial: int


# RawModels are manually defined models in 'utils/models/models.json'
class RawModel(BaseModel):
    new: bool = False
    status: Literal["archived", "missing_data", "disabled", "enabled"] | None = (
        "enabled"
    )
    id: str
    simple_name: str
    license: str
    fully_open_source: bool = False
    release_date: str = Field(pattern=r"^[0-9]{2}/[0-9]{4}$")
    params: int | float
    active_params: int | float | None = None
    arch: str
    reasoning: bool | Literal["hybrid"] = False
    quantization: Literal["q4", "q8"] | None = None
    url: str | None = None  # FIXME required?
    endpoint: Endpoint | None = None
    desc: str
    size_desc: str
    fyi: str
    pricey: bool = False  # FIXME move to endpoint?

    @field_validator("arch", mode="after")
    @classmethod
    def check_arch_exists(cls, value: str, info: ValidationInfo) -> str:
        if value.replace("maybe-", "") not in info.context["archs"]:
            raise PydanticCustomError(
                "missing_arch", f"Missing arch '{value}' infos in 'archs.json'."
            )

        return value

    @model_validator(mode="after")
    def check_endpoint(self):
        if self.status == "enabled" and not self.endpoint:
            raise PydanticCustomError(
                "endpoint", "Model is enabled but no endpoint has been found."
            )
        return self


# Models are models definition generated with 'utils/models/build_models.py'
# as 'utils/models/generated-models.json'
class Model(RawModel):
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
        if not file_path.exists():
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


def filter_enabled_models(models: dict[str, Model]):
    enabled_models = {}
    for model_id, model_dict in models.items():
        if model_dict.get("status") == "enabled":
            try:
                if Endpoint.model_validate(model_dict.get("endpoint")):
                    enabled_models[model_id] = model_dict
            except:
                continue

    return enabled_models


class ConversationMessage(BaseModel):
    role: str
    content: str
    metadata: dict[str, Any] | None = None

    # Custom validation to ensure 'output_tokens' is present for 'assistant' roles
    @model_validator(mode="after")
    def check_assistant_metadata(self) -> "ConversationMessage":
        if self.role == "assistant":
            if not self.metadata or "output_tokens" not in self.metadata:
                raise ValueError(
                    "Assistant messages must have 'output_tokens' in metadata"
                )
        return self


ConversationMessages = RootModel[list[ConversationMessage]]


class Conversation(BaseModel):
    id: int
    # TODO: fuseau horaire
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
    ip: str | None = None
    model_pair_name: str
    # TODO: computed / added at dataset
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
