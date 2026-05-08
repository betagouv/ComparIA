from datetime import datetime
from typing import Annotated

from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel, String

from backend.arena.models import ErrorDetails
from backend.config import CountryPortal, CustomModelsSelection, SelectionMode
from utils.database.utils import ArchivedReason

from .messages import SystemMessage, SystemMessageRead
from .turn import Turn, TurnPublic, TurnRead

SystemMessageId = Annotated[
    int | None, Field(foreign_key="system_message.id", unique=True)
]


class ComparisonBase(SQLModel):
    created_at: Annotated[
        datetime, Field(default_factory=datetime.now, sa_type=TIMESTAMP)
    ]
    updated_at: Annotated[
        datetime, Field(default_factory=datetime.now, sa_type=TIMESTAMP)
    ]
    session_hash: str
    ip: str  # WARNING: PII
    visitor_id: str | None = None
    country_portal: Annotated[CountryPortal, Field(sa_type=String)]
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
    llm_analyze_failed: bool | None = None
    contains_pii: bool | None = None
    contains_spam: bool | None = None
    short_summary: str | None = None
    keywords: Annotated[list[str] | None, Field(sa_type=JSONB)] = None
    categories: Annotated[list[str] | None, Field(sa_type=JSONB)] = None
    languages: Annotated[list[str] | None, Field(sa_type=JSONB)] = None

    # archived metadata
    archived: bool | None = None
    archived_reason: Annotated[ArchivedReason | None, Field(sa_type=String)] = None
    archived_at: datetime | None = None


class Comparison(ComparisonWithAnalyzeData, table=True):
    id: int | None = Field(default=None, primary_key=True)

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
    id: int
    system_msg_a: SystemMessageRead | None
    system_msg_b: SystemMessageRead | None
    turns: list[TurnRead]


class ComparisonPublic(SQLModel):
    id: int
    session_hash: str
    mode: SelectionMode
    custom_models_selection: CustomModelsSelection
    error: ErrorDetails | None
    turns: list[TurnPublic]
