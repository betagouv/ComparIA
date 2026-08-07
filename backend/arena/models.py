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

# Recordings whose transcription is still in the prompt box. Sent so the stored
# audio can be pointed at the turn its text ended up in, which is what makes the
# raw transcription comparable to what the user finally sent.
RecordingIdsField: list[UUID] = Field(default_factory=list, max_length=20)


class TranscribeResponse(BaseModel):
    text: str
    # None when the instance keeps nothing, so the browser has no id to send on.
    recording_id: UUID | None = None


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
    recording_ids: list[UUID] = RecordingIdsField

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
    recording_ids: list[UUID] = RecordingIdsField

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
