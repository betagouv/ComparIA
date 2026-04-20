from typing import Annotated, Literal

from sqlmodel import Field, SQLModel, String


class LLMMessage(SQLModel, table=True):
    __tablename__ = "llm_message"

    id: Annotated[int | None, Field(primary_key=True)] = None
    role: Annotated[Literal["assistant"], Field(sa_type=String)] = "assistant"

    content: str
    reasoning_content: str | None = None

    generation_id: str | None = None
    tokens: int | None = None
    duration: float | None = None
    is_cached: bool = False
