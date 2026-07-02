from typing import Annotated

from sqlmodel import Field

from ..utils import BaseDBModel


class LLMEndpointBase(BaseDBModel):
    name: Annotated[str, Field(index=True)]
    api_type: str
    api_base: str | None = None
    api_version: str | None = None


class LLMEndpointPrivate(LLMEndpointBase):
    api_key: str | None = None


class LLMEndpoint(LLMEndpointPrivate, table=True):
    """
    LLM endpoint configuration for API calls.

    Attributes
    ----------
    name
        Readable endpoint name (e.g. 'OpenRouter').
    api_type
        API format (e.g. 'openrouter' or 'openai' for OpenAI-compatible APIs).
    api_base
        Base URL for the API endpoint.
    api_version
        API version (optional)
    api_key
        API secret key.
    """

    __tablename__ = "llm_endpoint"


class LLMEndpointUpsert(LLMEndpointPrivate):
    pass


class LLMEndpointPublic(LLMEndpointBase):
    pass
