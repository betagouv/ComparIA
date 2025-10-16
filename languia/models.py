from pydantic import BaseModel, Field, RootModel, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from typing import Any, Literal, Tuple, get_args, Annotated


class License(BaseModel):
    license: str
    license_desc: str
    distribution: Literal["api-only", "open-weights", "fully-open-source"]
    reuse: bool
    commercial_use: bool | None = None
    reuse_specificities: str | None = None
    commercial_use_specificities: str | None = None


class Endpoint(BaseModel):
    api_type: str | None = "openai"
    api_base: str | None = None
    api_model_id: str


class Model(BaseModel):
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


class Organisation(BaseModel):
    name: str
    icon_path: str | None = None  # FIXME required?
    proprietary_license_desc: str | None = None
    proprietary_reuse: bool = False
    proprietary_commercial_use: bool | None = None
    proprietary_reuse_specificities: str | None = None
    proprietary_commercial_use_specificities: str | None = None
    models: list[Model]


Licenses = RootModel[list[License]]
Orgas = RootModel[list[Organisation]]

from pydantic import BaseModel, Field, model_validator, RootModel
from typing import List, Optional, Dict, Any
import datetime


class ConversationMessage(BaseModel):
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None

    # Custom validation to ensure 'output_tokens' is present for 'assistant' roles
    @model_validator(mode="after")
    def check_assistant_metadata(self) -> "ConversationMessage":
        if self.role == "assistant":
            if not self.metadata or "output_tokens" not in self.metadata:
                raise ValueError(
                    "Assistant messages must have 'output_tokens' in metadata"
                )
        return self


ConversationMessages = RootModel[List[ConversationMessage]]


class Conversation(BaseModel):
    id: int
    # TODO: fuseau horaire
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.now)
    model_a_name: str
    model_b_name: str
    conversation_a: ConversationMessages
    conversation_b: ConversationMessages
    conv_turns: int = 0
    system_prompt_a: Optional[str] = None
    system_prompt_b: Optional[str] = None
    conversation_pair_id: str
    conv_a_id: str
    conv_b_id: str
    session_hash: str
    visitor_id: Optional[str] = None
    ip: Optional[str] = None
    model_pair_name: str
    # TODO: computed / added at dataset
    opening_msg: str
    archived: bool = False
    mode: Optional[str] = None
    custom_models_selection: Optional[Dict[str, Any]] = None
    short_summary: Optional[str] = None
    keywords: Optional[Dict[str, Any]] = None
    categories: Optional[Dict[str, Any]] = None
    languages: Optional[Dict[str, Any]] = None
    pii_analyzed: bool = False
    contains_pii: Optional[bool] = None
    total_conv_a_output_tokens: Optional[int] = None
    total_conv_b_output_tokens: Optional[int] = None
    ip_map: Optional[str] = None
    postprocess_failed: bool = False
