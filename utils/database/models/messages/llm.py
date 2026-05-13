from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String

from utils.validation import StripAndEmptyAsNone

from ..utils import ModelId


class LLMMessageBase(SQLModel):
    id: ModelId
    role: Annotated[Literal["assistant"], Field(sa_type=String)] = "assistant"

    content: str
    reasoning_content: str | None = None

    generation_id: str | None = None
    tokens: int | None = None
    duration: float | None = None
    is_cached: bool = False


class LLMMessageFinal(LLMMessageBase):
    content: Annotated[str, StripAndEmptyAsNone]
    reasoning_content: Annotated[str | None, StripAndEmptyAsNone]

    generation_id: str
    tokens: int
    duration: float
    is_cached: bool


class LLMMessage(LLMMessageFinal, table=True):
    __tablename__ = "llm_message"


class LLMMessageCreate(LLMMessageBase):
    content: str = ""
    reasoning_content: str = ""


class LLMMessageRead(LLMMessageFinal):
    pass
