from typing import Annotated, Literal
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import AfterValidator, model_validator
from pydantic.networks import HttpUrl
from pydantic_core import PydanticCustomError
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from utils.validation import NonEmptyStr

from ..utils import BaseDBModel, Datetime, OptionalDatetime
from .constants import LLMArchKind, LLMStatus
from .endpoint import LLMEndpoint
from .lab import LLMLab
from .license import LLMLicense

FIELDS = {
    "lab_id": {
        "title": "Lab",
        "description": "The lab that developed the LLM, create it first if not already available",
    },
    "license_id": {
        "title": "License",
        "description": "The LLM's license, create it first if not already available",
    },
    "endpoint_id": {
        "title": "Endpoint",
        "description": "The LLM's endpoint information, create it first if not already available",
    },
    "human_id": {
        "title": "Readable id",
        "description": "(legacy id), usually the LLM id specified in 'api_model_id'",
    },
    "api_model_id": {
        "title": "API model id",
        "description": "Complete identifier used for API calls.",
    },
    "status": {
        "description": "enabled: callable and displayed in llm list + rankings; archived: not callable but displayed in llm list + rankings; disabled: not callable and hidden in llm list + rankings.",
    },
    "name": {
        "title": "Readable name",
    },
    "rate_limited": {
        "description": "Apply rate limits (usually for high API costs LLMs).",
    },
    "release_date": {},
    "knowledge_cutoff": {
        "description": "Date after which the LLM no longer has knowledge.",
    },
    "arch": {
        "description": "LLM architecture, Use `maybe-*` if information is not confirmed.",
    },
    "params": {
        "description": "Total parameters in billions.",
    },
    "active_params": {
        "description": "Active parameters in billions (only for MoE LLMs).",
    },
    "context_tokens": {
        "description": "Size of its context window in tokens.",
    },
    "quantization": {
        "description": "Quantization scheme applied (q4, q8, or None for full precision).",
    },
    "inputs": {
        "title": "Modalities",
        "description": "What kind of media the LLM can have in input.",
    },
    "public_weights": {
        "description": "Whether the LLM weights are public.",
    },
    "public_training_data": {
        "description": "Whether the LLM training data is public.",
    },
    "public_training_code": {
        "description": "Whether the LLM training code is public.",
    },
    "eu_hostable": {
        "description": "Whether the LLM is hostable in the EU.",
    },
    "price_in": {
        "description": "Price per million input tokens in $.",
    },
    "price_out": {
        "description": "Price per million output tokens in $.",
    },
    "system_prompt": {
        "description": "System message to add in llm call if specified",
    },
    "links": {
        "description": "List of links to display in LLM card.",
    },
}


class Link(SQLModel):
    text: NonEmptyStr
    url: HttpUrl


class LLMDataBase(BaseDBModel):
    status: Annotated[LLMStatus, Field(sa_type=String, **FIELDS["status"])]
    name: Annotated[NonEmptyStr, Field(**FIELDS["name"])]
    human_id: Annotated[
        NonEmptyStr, Field(index=True, unique=True, **FIELDS["human_id"])
    ]
    api_model_id: Annotated[
        NonEmptyStr | None, Field(default=None, **FIELDS["api_model_id"])
    ]  # used to computed litellm args alongside LLMEndpoint data
    endpoint_id: Annotated[
        UUID | None,
        Field(default=None, foreign_key="llm_endpoint.id", **FIELDS["endpoint_id"]),
    ]
    rate_limited: Annotated[bool, Field(**FIELDS["rate_limited"])]  # previous "pricey"
    lab_id: Annotated[UUID, Field(foreign_key="llm_lab.id", **FIELDS["lab_id"])]
    release_date: Annotated[Datetime, Field(**FIELDS["release_date"])]
    knowledge_cutoff: Annotated[
        OptionalDatetime, Field(default=None, **FIELDS["knowledge_cutoff"])
    ]
    license_id: Annotated[
        UUID, Field(foreign_key="llm_license.id", **FIELDS["license_id"])
    ]
    public_weights: Annotated[bool, Field(**FIELDS["public_weights"])]
    public_training_data: Annotated[bool, Field(**FIELDS["public_training_data"])]
    public_training_code: Annotated[bool, Field(**FIELDS["public_training_code"])]
    eu_hostable: Annotated[bool, Field(**FIELDS["eu_hostable"])]
    arch: Annotated[LLMArchKind, Field(sa_type=String, **FIELDS["arch"])]
    params: Annotated[float, Field(**FIELDS["params"])]
    active_params: Annotated[
        float | None, Field(default=None, **FIELDS["active_params"])
    ]
    context_tokens: Annotated[
        int | None, Field(default=None, **FIELDS["context_tokens"])
    ]
    quantization: Annotated[
        Literal["q4", "q8"] | None,
        Field(default=None, sa_type=String, **FIELDS["quantization"]),
    ]
    inputs: Annotated[
        list[Literal["text", "image", "audio", "video"]],
        Field(sa_type=JSONB, **FIELDS["inputs"]),
    ]
    price_in: Annotated[float, Field(**FIELDS["price_in"])]
    price_out: Annotated[float, Field(**FIELDS["price_out"])]
    system_prompt: Annotated[
        NonEmptyStr | None, Field(default=None, **FIELDS["system_prompt"])
    ]
    links: Annotated[
        list[Link],
        Field(sa_type=JSONB, **FIELDS["links"]),
        AfterValidator(jsonable_encoder),
    ] = []


class LLMData(LLMDataBase, table=True):
    """
    LLM definition.

    Contains basic LLM information and links to licence, lab and endpoint.
    """

    __tablename__ = "llm_data"

    lab: LLMLab = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[LLMData.lab_id]", "lazy": "joined"}
    )
    license: LLMLicense = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[LLMData.license_id]",
            "lazy": "joined",
        }
    )
    endpoint: LLMEndpoint | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[LLMData.endpoint_id]",
            "lazy": "joined",
        }
    )


class LLMDataUpsert(LLMDataBase):
    @model_validator(mode="after")
    def check_active_params_is_defined_if_moe(self):
        """
        Assert active_params is defined if arch == "moe".

        Checked on the model and not the field: active_params defaults to None,
        and field validators do not run on a field the payload leaves out.
        """
        if "moe" in self.arch and self.active_params is None:
            raise PydanticCustomError(
                "missing_active_params",
                f"LLM's arch is '{self.arch}' and requires 'active_params' to be defined.",
            )

        return self

    @model_validator(mode="after")
    def check_endpoint(self):
        """
        Disable LLM if endpoint is not defined.
        """
        if self.status == "enabled" and (not self.endpoint_id or not self.api_model_id):
            self.status = "disabled"
        return self


class LLMDataPublic(LLMDataBase):
    # add license + lab?
    pass
