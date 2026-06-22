import uuid
from typing import TYPE_CHECKING, Annotated, Literal, get_args

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from backend.config import NegativePref, PositivePref, TurnChoice
from utils.validation import StripAndEmptyAsNone

from .messages import (
    LLMMessage,
    LLMMessageCreate,
    LLMMessageRead,
    UserMessage,
    UserMessageRead,
)
from .utils import AutoDatetime, ModelId, OptionalDatetime

if TYPE_CHECKING:
    from .comparison import Comparison

BotPos = Literal["a", "b"]
BOT_POS: tuple[BotPos, ...] = get_args(BotPos)
LLMMessageId = Annotated[
    uuid.UUID | None, Field(foreign_key="llm_message.id", unique=True)
]
KeywordAnnotations = Annotated[
    list[PositivePref] | list[NegativePref], Field(sa_type=JSONB)
]


class TurnBase(SQLModel):
    id: ModelId
    comparison_id: Annotated[uuid.UUID, Field(foreign_key="comparison.id")]
    created_at: AutoDatetime
    updated_at: AutoDatetime
    choice: Annotated[TurnChoice | None, Field(sa_type=String)] = None
    # Set when the user submits their choice vote (once per turn). Used to
    # measure how long they took to vote after both models finished.
    voted_at: OptionalDatetime = None

    # a
    llm_msg_a_id: LLMMessageId = None
    keyword_annotations_a: KeywordAnnotations = []
    custom_annotation_a: str | None = None

    # b
    llm_msg_b_id: LLMMessageId = None
    keyword_annotations_b: KeywordAnnotations = []
    custom_annotation_b: str | None = None


class Turn(TurnBase, table=True):
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
    user_msg: UserMessageRead
    llm_msg_a: LLMMessageRead | None
    llm_msg_b: LLMMessageRead | None


class TurnPublic(SQLModel):
    id: uuid.UUID
    user_msg: UserMessageRead
    choice: TurnChoice | None

    llm_msg_a: LLMMessageCreate | None
    keyword_annotations_a: KeywordAnnotations
    custom_annotation_a: str | None = ""

    llm_msg_b: LLMMessageCreate | None
    keyword_annotations_b: KeywordAnnotations
    custom_annotation_b: str | None = ""


class TurnVoteChoice(SQLModel):
    turn_id: Annotated[uuid.UUID, Field(exclude=True)]
    choice: TurnChoice


# TODO assert keywords are positive/negative depending on vote choice
class TurnVoteAnnotate(SQLModel):
    turn_id: Annotated[uuid.UUID, Field(exclude=True)]
    pos: Annotated[BotPos, Field(exclude=True)]
    keyword_annotations: list[PositivePref] | list[NegativePref]
    custom_annotation: Annotated[str | None, StripAndEmptyAsNone]
