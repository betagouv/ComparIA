from datetime import datetime
from typing import Annotated

from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlmodel import Field, Relationship, SQLModel, String

from backend.config import CustomModelsSelection, SelectionMode
from utils.database.utils import ArchivedReason

from .messages import SystemMessage
from .turn import Turn

SystemMessageId = Annotated[
    int | None, Field(foreign_key="system_message.id", unique=True)
]


class Comparison(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: Annotated[
        datetime, Field(default_factory=datetime.now, sa_type=TIMESTAMP)
    ]
    updated_at: Annotated[
        datetime, Field(default_factory=datetime.now, sa_type=TIMESTAMP)
    ]
    session_hash: str
    ip: str  # WARNING: PII
    visitor_id: str | None = None
    cohorts: str | None = None
    mode: Annotated[SelectionMode, Field(sa_type=String)]
    custom_models_selection: Annotated[CustomModelsSelection, Field(sa_type=JSONB)] = (
        None
    )

    turns: list[Turn] = Relationship(back_populates="comparison")

    # a
    llm_id_a: str
    system_msg_a_id: SystemMessageId = None
    system_msg_a: SystemMessage | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Turn.system_msg_a_id]",
            "lazy": "joined",
        }
    )
    # b
    llm_id_b: str
    system_msg_b_id: SystemMessageId = None
    system_msg_b: SystemMessage | None = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "[Turn.system_msg_b_id]",
            "lazy": "joined",
        }
    )

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
