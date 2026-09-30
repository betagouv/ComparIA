from datetime import datetime
from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String

from utils.validation import StripAndEmptyAsNone

from ..utils import ModelId, OptionalDatetime


class LLMMessageBase(SQLModel):
    id: ModelId
    role: Annotated[Literal["assistant"], Field(sa_type=String)] = "assistant"
    created_at: OptionalDatetime = None
    responded_at: OptionalDatetime = None
    updated_at: OptionalDatetime = None

    content: str
    reasoning_content: str | None = None

    generation_id: str | None = None
    tokens: int | None = None
    is_cached: bool = False


class LLMMessageFinal(LLMMessageBase):
    created_at: datetime
    responded_at: datetime
    updated_at: datetime
    content: Annotated[str, StripAndEmptyAsNone]
    reasoning_content: Annotated[str | None, StripAndEmptyAsNone]

    generation_id: str
    tokens: int
    is_cached: bool


class LLMMessage(LLMMessageFinal, table=True):
    __tablename__ = "llm_message"


class LLMMessageCreate(LLMMessageBase):
    content: str = ""
    # Nullable: StripAndEmptyAsNone persists empty reasoning_content as NULL,
    # so DB-loaded rows must validate back through LLMMessageCreate.
    reasoning_content: str | None = ""

    # This is the shape the browser sees, on every streamed chunk and again in
    # TurnPublic, so these three stay server-side: the provider's own id
    # prefixes name the provider, and the token count and cache hit are
    # per-model tells. They are still set and still saved, only not sent.
    # Reveal reports the token counts once the vote is in.
    generation_id: str | None = Field(default=None, exclude=True)
    tokens: int | None = Field(default=None, exclude=True)
    is_cached: bool = Field(default=False, exclude=True)


class LLMMessageRead(LLMMessageFinal):
    pass
