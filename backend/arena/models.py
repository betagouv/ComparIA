"""
Data validation models using Pydantic.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.arena.captcha import verify_altcha_token
from backend.arena.spam_detection import is_spam
from backend.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    DEFAULT_SELECTION_MODE,
    CustomModelsSelection,
    SelectionMode,
)

# Request/Response models for FastAPI endpoints
PromptField = Field(min_length=1, max_length=BLIND_MODE_INPUT_CHAR_LEN_LIMIT)


class AddFirstTextBody(BaseModel):
    """Request body for add_first_text endpoint."""

    prompt_value: str = PromptField
    mode: SelectionMode = DEFAULT_SELECTION_MODE
    custom_models_selection: CustomModelsSelection = None
    # We force cohorts not to be None to make sure cohorts detection has been called on frontend
    cohorts: str
    altcha_token: str
    web_search: bool = False
    # One-time server proof returned with a warning for this exact prompt.
    warning_token: str | None = None

    @field_validator("custom_models_selection")
    @classmethod
    def check_custom_models_selection(
        cls, v: CustomModelsSelection
    ) -> CustomModelsSelection:
        # `pick_two` parses these as UUIDs and only knows what to do with one or
        # two of them. Left unchecked, a third element or a non-UUID string
        # crashes deep in the picker as a 500; here it is a plain 422.
        if v is None:
            return v
        if len(v) > 2:
            raise ValueError("At most two models can be selected.")
        for llm_id in v:
            UUID(llm_id)
        return v

    @field_validator("prompt_value")
    @classmethod
    def check_spam(cls, v: str) -> str:
        if is_spam(v):
            raise ValueError(
                "This prompt format is not allowed. Please use natural language."
            )
        return v

    @field_validator("altcha_token")
    @classmethod
    def check_altcha(cls, v: str) -> str:
        ok, error = verify_altcha_token(v)
        if not ok:
            raise ValueError(f"Vérification anti-robot échouée : {error}")
        return v


class AddTextBody(BaseModel):
    """Request body for add_text endpoint."""

    message: str = PromptField
    altcha_token: str
    warning_token: str | None = None

    @field_validator("message")
    @classmethod
    def check_spam(cls, v: str) -> str:
        if is_spam(v):
            raise ValueError(
                "This prompt format is not allowed. Please use natural language."
            )
        return v

    @field_validator("altcha_token")
    @classmethod
    def check_altcha(cls, v: str) -> str:
        ok, error = verify_altcha_token(v)
        if not ok:
            raise ValueError(f"Vérification anti-robot échouée : {error}")
        return v
