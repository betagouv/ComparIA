import datetime
from pydantic import BaseModel, Field, RootModel, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from typing import Any, Literal

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


Licenses = RootModel[list[License]]
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
