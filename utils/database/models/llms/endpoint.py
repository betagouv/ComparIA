from typing import Annotated

from sqlmodel import Field

from utils.validation import NonEmptyStr

from ..utils import BaseDBModel

FIELDS = {
    "name": {"description": "Readable endpoint name (e.g. 'OpenRouter')."},
    "api_type": {
        "title": "Api type",
        "description": "API format (e.g. 'openrouter' or 'openai' for OpenAI-compatible APIs).",
    },
    "api_base": {
        "title": "API base URL",
        "description": "Base URL for the API endpoint.",
    },
    "api_version": {"title": "API version", "description": "API version (optional)"},
    "api_key": {
        "title": "API secret key",
        "description": "if not given, all LLMs depending on this endpoint will be disabled.",
    },
}


class LLMEndpointBase(BaseDBModel):
    name: Annotated[NonEmptyStr, Field(index=True, **FIELDS["name"])]
    api_type: Annotated[NonEmptyStr, Field(**FIELDS["api_type"])]
    api_base: Annotated[NonEmptyStr | None, Field(**FIELDS["api_base"])] = None
    api_version: Annotated[NonEmptyStr | None, Field(**FIELDS["api_version"])] = None


class LLMEndpointPrivate(LLMEndpointBase):
    api_key: Annotated[str | None, Field(**FIELDS["api_key"])] = None


class LLMEndpoint(LLMEndpointPrivate, table=True):
    """
    LLM endpoint configuration for API calls.
    """

    __tablename__ = "llm_endpoint"


class LLMEndpointUpsert(LLMEndpointPrivate):
    pass


class LLMEndpointPublic(LLMEndpointBase):
    """What the admin panel is allowed to see: whether a key is set, not the key.

    The panel only ever needed the boolean, and a key that reaches the browser
    also reaches devtools, the cache and anything that logs the response.
    """

    has_api_key: bool = False
