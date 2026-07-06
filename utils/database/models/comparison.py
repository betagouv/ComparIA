import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, computed_field
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from backend.config import CustomModelsSelection, SelectionMode
from utils.validation import StripAndEmptyAsNone

from .turn import Turn, TurnPublic, TurnRead
from .utils import BaseDBModel, BotPos, OptionalDatetime

ArchivedReason = Literal[
    # FIXME remove commented archived reasons (should not happen anymore)
    "corrupted_no_model",
    "corrupted_against_self",  # some Comparison llm_id_(a|b) are equal
    "corrupted_no_response",  # Comparison has no LLMMessage at all
    "corrupted_response_all_none",  # some Comparison Turns side has all its LLMMessage.content as None
    "corrupted_response_last_none",  # some Comparison Turn side has its last LLMMessage.content as None
    "corrupted_response_some_none",  # some Comparison Turn side has at least one LLMMessage.content as None
    "corrupted_response_all_empty",  # some Comparison Turn side has all its LLMMessage.content as ''
    "corrupted_response_last_empty",  # some Comparison Turn side has its last LLMMessage.content as ''
    "corrupted_response_some_empty",  # some Comparison Turn side has at least one LLMMessage.content as ''
    "corrupted_model_stream",  # some Comparison Turn side has at least one LLMMessage.content with ModelResponse or ModelResponseStream in it
    "corrupted_not_equal_length",
    # "corrupted_out_of_range_reactions",
    # "corrupted_to_model_msg_reactions",
    # "corrupted_no_choice_votes",
    # "duplicate",
    # "duplicate_has_vote",
    "spam",
    "pii",
    "unknown_llm",
    "blacklist_grok",
    "unknown",
]
# TODO could be fixed?
# - "corrupted_response_(last|some)_(none|empty)":
#   - remove corresponding UserMessage + LLMMessage
# - "corrupted_model_stream": reparse LLMMessage content

LLMDataId = Annotated[uuid.UUID, Field(foreign_key="llm_data.id")]


class ErrorDetails(BaseModel):
    message: str
    # turn_index: int
    pos: BotPos | None = None
    is_timeout: bool = False


class ComparisonBase(BaseDBModel):
    ip: str  # WARNING: PII
    visitor_id: str | None = None
    user_id: Annotated[uuid.UUID | None, Field(foreign_key="auth_user.id")] = None
    anonymous_user_hash: str | None = None
    cohorts: Annotated[str | None, StripAndEmptyAsNone] = None
    mode: Annotated[SelectionMode, Field(sa_type=String)]
    custom_models_selection: Annotated[CustomModelsSelection, Field(sa_type=JSONB)] = (
        None
    )

    # a
    llm_id_a: LLMDataId
    system_msg_a: str | None = None

    # b
    llm_id_b: LLMDataId
    system_msg_b: str | None = None

    error: Annotated[ErrorDetails | None, Field(sa_type=JSONB)] = None


class ComparisonWithAnalyzeData(ComparisonBase):
    # LLM analyze metadata
    llm_analyzed: bool | None = None
    contains_pii: bool | None = None
    contains_spam: bool | None = None
    short_summary: str | None = None
    keywords: Annotated[list[str] | None, Field(sa_type=JSONB)] = None
    categories: Annotated[list[str] | None, Field(sa_type=JSONB)] = None
    languages: Annotated[list[str] | None, Field(sa_type=JSONB)] = None

    # archived metadata
    archived: bool | None = None
    archived_reason: Annotated[ArchivedReason | None, Field(sa_type=String)] = None
    archived_at: OptionalDatetime = None


class Comparison(ComparisonWithAnalyzeData, table=True):
    turns: list[Turn] = Relationship(
        back_populates="comparison",
        cascade_delete=True,
        sa_relationship_kwargs={"lazy": "selectin", "order_by": "Turn.created_at"},
    )


class ComparisonCreate(ComparisonBase):
    pass


class ComparisonRead(ComparisonBase):
    turns: list[TurnRead]


class ComparisonPublic(SQLModel):
    id: uuid.UUID
    mode: SelectionMode
    custom_models_selection: CustomModelsSelection
    error: ErrorDetails | None
    turns: list[TurnPublic]


class ComparisonArchiveUpdate(SQLModel):
    archived: Literal[True] = True
    archived_reason: ArchivedReason
    archived_at: datetime


class ComparisonUnarchiveUpdate(SQLModel):
    archived: Literal[None, False] = None
    archived_reason: Literal[None] = None
    archived_at: Literal[None] = None


class ComparisonLLMAnalysisUpdate(SQLModel):
    """
    Model to validate LLM analysis and update Comparison
    """

    llm_analyzed: Literal[True] = True
    contains_pii: bool
    contains_spam: bool
    short_summary: str
    keywords: list[str]
    categories: list[str]
    languages: list[str]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def archived(self) -> bool:
        return self.contains_pii or self.contains_spam

    @computed_field  # type: ignore[prop-decorator]
    @property
    def archived_reason(self) -> Literal["spam", "pii"] | None:
        if self.contains_spam:
            return "spam"
        if self.contains_pii:
            return "pii"
        return None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def archived_at(self) -> datetime | None:
        return datetime.now() if self.archived else None


class ComparisonLLMAnalysisFailedUpdate(SQLModel):
    """
    Model to update Comparison when LLM analysis fails.
    """

    llm_analyzed: Literal[False] = False
    # FIXME archive it directly?
    # archived: Literal[True] = True
    # archived_reason: Literal["failed_analysis"] = "failed_analysis"
    # archived_at: AutoDatetime
