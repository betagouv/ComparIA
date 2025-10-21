import datetime
from pathlib import Path
from pydantic import (
    BaseModel,
    Field,
    RootModel,
    ValidationError,
    model_validator,
    ValidationInfo,
    computed_field,
    field_validator,
)
from pydantic_core import PydanticCustomError
from typing import Any, Literal

ROOT_PATH = Path(__file__).parent.parent
FRONTEND_PATH = ROOT_PATH / "frontend"

Distribution = Literal["api-only", "open-weights", "fully-open-source"]


class License(BaseModel):
    license: str
    license_desc: str
    distribution: Distribution
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


class Endpoint(BaseModel):
    api_type: str | None = "openai"
    api_base: str | None = None
    api_model_id: str


# RawModels are manually defined models in 'utils/models/models.json'
class RawModel(BaseModel):
    new: bool = False
    status: Literal["archived", "missing_data", "disabled", "enabled"] | None = (
        "enabled"
    )
    id: str
    simple_name: str
    license: str
    fully_open_source: bool | None = None
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
    pricey: bool = False

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

    @field_validator("distribution", mode="before")
    @classmethod
    def check_distribution(
        cls, value: Distribution, info: ValidationInfo
    ) -> Distribution:
        if info.data["fully_open_source"]:
            value = "fully-open-source"

        return value


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

        return value


Licenses = RootModel[list[License]]
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
