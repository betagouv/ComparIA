from typing import Annotated, Literal
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from pydantic import AfterValidator
from pydantic.networks import HttpUrl
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from ..utils import BaseDBModel, Datetime, OptionalDatetime
from .constants import LLMArchKind, LLMStatus
from .endpoint import LLMEndpoint
from .lab import LLMLab
from .license import LLMLicense


class Link(SQLModel):
    text: str
    url: HttpUrl


class LLMDataBase(BaseDBModel):
    lab_id: Annotated[UUID, Field(foreign_key="llm_lab.id")]
    license_id: Annotated[UUID, Field(foreign_key="llm_license.id")]
    endpoint_id: Annotated[UUID | None, Field(foreign_key="llm_endpoint.id")]

    api_model_id: str | None  # used to computed litellm args alongside LLMEndpoint data
    status: Annotated[LLMStatus, Field(sa_type=String)]
    name: str
    rate_limited: bool  # previous "pricey"
    release_date: Datetime
    knowledge_cutoff: OptionalDatetime
    arch: Annotated[LLMArchKind, Field(sa_type=String)]
    params: float
    active_params: float | None
    context_tokens: int | None
    quantization: Annotated[Literal["q4", "q8"] | None, Field(sa_type=String)]
    inputs: Annotated[
        list[Literal["text", "image", "audio", "video"]], Field(sa_type=JSONB)
    ]
    public_weights: bool
    public_training_data: bool
    public_training_code: bool
    eu_hostable: bool
    price_in: float
    price_out: float
    system_prompt: str | None
    links: Annotated[
        list[Link], Field(sa_type=JSONB), AfterValidator(jsonable_encoder)
    ] = []


class LLMData(LLMDataBase, table=True):
    """
    LLM definition.

    Contains basic LLM information and links to licence, lab and endpoint.

    Attributes
    ----------
    human_id
        Readable id (legacy id), usually the id specified in `api_model_id`
        `'{labid}/{llmid}'`.
    api_model_id
        Identifier used in API calls.
    status
        Current status:
          - 'enabled': callable and displayed in llm list + rankings;
          - 'archived': not callable but displayed in llm list + rankings,
          - 'disabled': not callable and hidden in llm list + rankings.
    name
        Readable name.
    rate_limited
        Apply rate limits (usually for high API costs LLMs).
    release_date
        Release date.
    knowledge_cutoff
        Date after which the LLM no longer has knowledge.
    arch
        LLM architecture, Use `maybe-*` if information is not confirmed.
    params
        Total parameters in billions.
    active_params
        Active parameters in billions (only for MoE LLMs).
    context_tokens
        Size of its context window in tokens.
    quantization
        Quantization scheme applied (q4, q8, or None for full precision).
    inputs
        What kind of media the LLM can have in input.
    public_weights
        Whether the LLM weights are public.
    public_training_data
        Whether the LLM training data is public.
    public_training_code
        Whether the LLM training code is public.
    eu_hostable
        Whether the LLM is hostable in the EU.
    price_in
        Price per million input tokens in €.
    price_out
        Price per million output tokens in €.
    system_prompt
        System message to add in llm call if specified
    links
        List of links to display in LLM card.
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
    # FIXME add validator disabled = not endpoint or not api model id
    pass


class LLMDataPublic(LLMDataBase):
    # add license + lab?
    pass


# Computed


# class LLMFinalData(LLMData):
#     """
#     Computed model
#     """

#     # consumption data
#     required_ram: int  # computed from params?

#     # Linked data
#     lab: LLMLab
#     license: LLMLicense
#     endpoint: LLMEndpoint
