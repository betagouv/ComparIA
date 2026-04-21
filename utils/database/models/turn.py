from typing import TYPE_CHECKING, Annotated

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from backend.config import NegativePref, PositivePref, TurnChoice

from .messages import LLMMessage, LLMMessageRead, UserMessage, UserMessageRead

if TYPE_CHECKING:
    from .comparison import Comparison

LLMMessageId = Annotated[int | None, Field(foreign_key="llm_message.id", unique=True)]
KeywordAnnotations = Annotated[
    list[PositivePref] | list[NegativePref], Field(sa_type=JSONB)
]


class TurnBase(SQLModel):
    comparison_id: Annotated[int, Field(foreign_key="comparison.id")]
    choice: Annotated[TurnChoice | None, Field(sa_type=String)] = None

    # a
    llm_msg_a_id: LLMMessageId = None
    keyword_annotations_a: KeywordAnnotations = []
    custom_annotation_a: str | None = None

    # b
    llm_msg_b_id: LLMMessageId = None
    keyword_annotations_b: KeywordAnnotations = []
    custom_annotation_b: str | None = None


class Turn(TurnBase, table=True):
    id: int | None = Field(default=None, primary_key=True)

    comparison: "Comparison" = Relationship(back_populates="turns")
    user_msg: UserMessage = Relationship(
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"}
    )
    llm_msg_a: LLMMessage | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Turn.llm_msg_a_id]", "lazy": "joined"}
    )
    llm_msg_b: LLMMessage | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Turn.llm_msg_b_id]", "lazy": "joined"}
    )


class TurnCreate(TurnBase):
    user_msg: UserMessage


class TurnRead(TurnBase):
    id: int
    user_msg: UserMessageRead
    llm_msg_a: LLMMessageRead | None
    llm_msg_b: LLMMessageRead | None
