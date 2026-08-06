import uuid
from typing import TYPE_CHECKING, Annotated

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from backend.config import TurnChoice
from utils.validation import StripAndEmptyAsNone

from .messages import (
    LLMMessage,
    LLMMessageCreate,
    LLMMessageRead,
    UserMessage,
    UserMessageRead,
)
from .prompt_check import PromptCheckResult
from .utils import BaseDBModel, BotPos, OptionalDatetime

if TYPE_CHECKING:
    from .comparison import Comparison

LLMMessageId = Annotated[
    uuid.UUID | None, Field(foreign_key="llm_message.id", unique=True)
]
# Vote tag keys. The vocabulary lives in the 'vote_tag' table, so keys are
# checked against the active tags when a vote comes in, not by this type.
KeywordAnnotations = Annotated[list[str], Field(sa_type=JSONB)]


class TurnBase(BaseDBModel):
    comparison_id: Annotated[uuid.UUID, Field(foreign_key="comparison.id")]
    choice: Annotated[TurnChoice | None, Field(sa_type=String)] = None
    # Set when the user submits their choice vote (once per turn). Used to
    # measure how long they took to vote after both models finished.
    voted_at: OptionalDatetime = None
    # Legacy prompt check format (replaced by "prompt_check_result")
    guardrail: Annotated[dict | None, Field(sa_type=JSONB)] = None

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
        cascade_delete=True,
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"},
    )
    llm_msg_a: LLMMessage | None = Relationship(
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[Turn.llm_msg_a_id]",
            "lazy": "joined",
            "single_parent": True,
        },
    )
    llm_msg_b: LLMMessage | None = Relationship(
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "[Turn.llm_msg_b_id]",
            "lazy": "joined",
            "single_parent": True,
        },
    )
    # One verdict per prompt check that ran on this turn's user prompt.
    # Not exposed in TurnPublic, intended for the -raw dataset, not the public one.
    prompt_check_result: PromptCheckResult | None = Relationship(
        cascade_delete=True,
        sa_relationship_kwargs={"uselist": False, "lazy": "joined"},
    )


class TurnCreate(TurnBase):
    user_msg: UserMessage
    prompt_check_result: PromptCheckResult | None


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


class TurnVoteAnnotate(SQLModel):
    turn_id: Annotated[uuid.UUID, Field(exclude=True)]
    pos: Annotated[BotPos, Field(exclude=True)]
    keyword_annotations: list[str]
    custom_annotation: Annotated[str | None, StripAndEmptyAsNone]
