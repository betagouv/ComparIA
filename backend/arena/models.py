"""
Data validation models using Pydantic.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.arena.captcha import verify_altcha_token
from backend.arena.limits import LimitSetting
from backend.arena.normalize import strip_hidden
from backend.config import (
    BLIND_MODE_INPUT_CHAR_LEN_LIMIT,
    DEFAULT_SELECTION_MODE,
    CustomModelsSelection,
    SelectionMode,
)

# Request/Response models for FastAPI endpoints
PromptField = Field(min_length=1)


def check_message(v: str) -> str:
    """Refuse a message over the length limit, hidden characters included, then
    drop the hidden ones. The key, unlike Pydantic's own sentence, is one the
    frontend can translate."""
    if len(v) > BLIND_MODE_INPUT_CHAR_LEN_LIMIT:
        raise ValueError("prompt_too_long")
    return strip_hidden(v)


class CaptchaBody(BaseModel):
    """A request that calls the models, so it must carry a solved captcha."""

    altcha_token: str

    @field_validator("altcha_token")
    @classmethod
    def check_altcha(cls, v: str) -> str:
        ok, error = verify_altcha_token(v)
        if not ok:
            raise ValueError("captcha_failed")
        return v


class AddFirstTextBody(CaptchaBody):
    """Request body for add_first_text endpoint."""

    prompt_value: str = PromptField
    mode: SelectionMode = DEFAULT_SELECTION_MODE
    custom_models_selection: CustomModelsSelection = None
    # We force cohorts not to be None to make sure cohorts detection has been called on frontend
    cohorts: str
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
    def check_prompt(cls, v: str) -> str:
        return check_message(v)


class AddTextBody(CaptchaBody):
    """Request body for add_text endpoint."""

    message: str = PromptField
    warning_token: str | None = None

    @field_validator("message")
    @classmethod
    def check_text(cls, v: str) -> str:
        return check_message(v)


class RetryBody(CaptchaBody):
    """Request body for retry endpoint. A retry calls both models again, so it
    takes the same proof of work as a new message."""


LimitKey = Literal["allowance_spent", "expensive_allowance_spent", "model_full_today"]


class LimitRefusal(BaseModel):
    """What a message refused on a limit carries beside its `detail` key, so
    the arena can say which limit it met and when it lifts."""

    # "session" is this person, "network" everyone behind their IP, None a
    # limit that applies to everyone.
    scope: Literal["session", "network"] | None
    resets_at: datetime | None
    resets_in: int | None
    # The models the refusal is about, when it is about some.
    llm_ids: list[UUID] = []


class LimitRefusalBody(BaseModel):
    """The body of a 429 on a limit. `detail` stays a string key, as on every
    other error, so a client that only reads `detail` still works."""

    detail: LimitKey
    limit: LimitRefusal


class SpentAllowance(BaseModel):
    """A spent allowance, told by who it is spent for and when it lifts."""

    scope: Literal["session", "network"]
    resets_at: datetime | None
    # The same, in seconds from now, so the page can count down on the
    # server's clock rather than its own.
    resets_in: int | None


class PausedLLM(BaseModel):
    """A model left out of this person's new comparisons until `until`:
    "allowance" while their expensive allowance is spent, "full" while the
    model's daily cap is."""

    id: UUID
    until: datetime | None
    reason: Literal["allowance", "full"]


class ArenaLimits(BaseModel):
    """
    What the arena may do for this person right now, read before they type.

    An allowance shows only once it is spent: before that, no field, no reset
    time, since watching one appear after a message would tell that the pair
    had an expensive model. No counter and no share either: the person learns
    that an allowance is spent and when it lifts, never how much their network
    sent. What is left: the moment an allowance runs out, the person learns
    that one of their recent pairs used an expensive model, not which one.
    """

    # The whole allowance: while spent, no message goes through.
    total: SpentAllowance | None
    # The expensive allowance, session or network, the one that lifts last.
    expensive: SpentAllowance | None
    paused_llms: list[PausedLLM]


# The admin's view of the limits, at /admin/limites.

# Largest value a Postgres INTEGER column holds.
_INT_MAX = 2_147_483_647


class AdminLimit(BaseModel):
    name: LimitSetting
    # In force: the stored value, else the default.
    value: int
    # The RATELIMIT_* env value, in force while none is stored.
    default: int
    stored: bool


class AdminLimits(BaseModel):
    limits: list[AdminLimit]
    # The last change to any limit, and the admin who made it.
    updated_at: datetime | None
    updated_by: str | None


class AdminLimitsPatch(BaseModel):
    """A field left out stays as it is; null puts it back on its default."""

    model_config = ConfigDict(extra="forbid")

    all_per_session: int | None = Field(default=None, ge=1, le=_INT_MAX)
    all_per_ip: int | None = Field(default=None, ge=1, le=_INT_MAX)
    expensive_per_session: int | None = Field(default=None, ge=1, le=_INT_MAX)
    expensive_per_ip: int | None = Field(default=None, ge=1, le=_INT_MAX)
    expected_answer_chars: int | None = Field(default=None, ge=0, le=_INT_MAX)


class LimitProposal(BaseModel):
    """A value the calibration proposes, with what the page needs to say why."""

    name: LimitSetting
    value: int
    # How many two-hour windows, or answers, the value was read from.
    sample: int
    # The percentile of those it was read from.
    percentile: int
    # Per session: about how many messages of a typical cost fit in it.
    messages: int | None = None
    # Per network: the class it makes room for, and the share of the
    # networks' windows that went past it.
    class_size: int | None = None
    over_share: float | None = None


class LimitsCalibration(BaseModel):
    days: int
    comparisons: int
    turns: int
    # The sample stopped at its cap: only the latest comparisons were read.
    capped: bool
    proposals: list[LimitProposal]
