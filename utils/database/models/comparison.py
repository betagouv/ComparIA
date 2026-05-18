import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import computed_field
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel, String

from backend.arena.models import ErrorDetails
from backend.config import CustomModelsSelection, SelectionMode
from utils.database.utils import ArchivedReason

from .messages import SystemMessage, SystemMessageRead
from .turn import Turn, TurnPublic, TurnRead
from .utils import AutoDatetime, ModelId, OptionalDatetime

SystemMessageId = Annotated[
    uuid.UUID | None, Field(foreign_key="system_message.id", unique=True)
]


class ComparisonBase(SQLModel):
    id: ModelId
    created_at: AutoDatetime
    updated_at: AutoDatetime
    session_hash: str
    ip: str  # WARNING: PII
    visitor_id: str | None = None
    cohorts: str | None = None
    mode: Annotated[SelectionMode, Field(sa_type=String)]
    custom_models_selection: Annotated[CustomModelsSelection, Field(sa_type=JSONB)] = (
        None
    )

    # a
    llm_id_a: str
    system_msg_a_id: SystemMessageId = None

    # b
    llm_id_b: str
    system_msg_b_id: SystemMessageId = None

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
    system_msg_a: SystemMessage | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Comparison.system_msg_a_id]",
            "lazy": "joined",
        }
    )
    system_msg_b: SystemMessage | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Comparison.system_msg_b_id]",
            "lazy": "joined",
        }
    )

    turns: list[Turn] = Relationship(
        back_populates="comparison", sa_relationship_kwargs={"lazy": "selectin"}
    )


class ComparisonCreate(ComparisonBase):
    pass


class ComparisonRead(ComparisonBase):
    system_msg_a: SystemMessageRead | None
    system_msg_b: SystemMessageRead | None
    turns: list[TurnRead]


class ComparisonPublic(SQLModel):
    id: uuid.UUID
    session_hash: str
    mode: SelectionMode
    custom_models_selection: CustomModelsSelection
    error: ErrorDetails | None
    turns: list[TurnPublic]


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
