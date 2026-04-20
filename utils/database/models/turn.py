from typing import TYPE_CHECKING, Annotated

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from backend.config import NegativePref, PositivePref, TurnChoice

from .messages import LLMMessage, UserMessage

if TYPE_CHECKING:
    from .comparison import Comparison

LLMMessageId = Annotated[int | None, Field(foreign_key="llm_message.id", unique=True)]
KeywordAnnotations = Annotated[
    list[PositivePref] | list[NegativePref], Field(sa_type=JSONB)
]


class Turn(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)

    comparison_id: Annotated[int, Field(foreign_key="comparison.id")]
    comparison: "Comparison" = Relationship(back_populates="turns")

    choice: Annotated[TurnChoice | None, Field(sa_type=String)]
    user_msg: UserMessage = Relationship(
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"}
    )

    # a
    llm_id_a: str
    llm_msg_a_id: LLMMessageId = None
    llm_msg_a: LLMMessage | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Turn.llm_msg_a_id]", "lazy": "joined"}
    )
    keyword_annotations_a: KeywordAnnotations = []
    custom_annotation_a: str | None = None

    # b
    llm_id_b: str
    llm_msg_b_id: LLMMessageId = None
    llm_msg_b: LLMMessage | None = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Turn.llm_msg_b_id]", "lazy": "joined"}
    )
    keyword_annotations_b: KeywordAnnotations = []
    custom_annotation_b: str | None = None
