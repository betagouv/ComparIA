import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import StringConstraints
from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel, String

from .utils import AutoDatetime, ModelId, OptionalDatetime

SuggestionLocale = Literal["fr", "da", "sv"]
SUGGESTION_CATEGORY_TITLE_MAX_LENGTH = 100
SUGGESTION_CATEGORY_DESCRIPTION_MAX_LENGTH = 300
SUGGESTION_CATEGORY_TOOLTIP_MAX_LENGTH = 300

SuggestionText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4_000)
]
CategoryTitle = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=SUGGESTION_CATEGORY_TITLE_MAX_LENGTH,
    ),
]
CategoryDescription = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=SUGGESTION_CATEGORY_DESCRIPTION_MAX_LENGTH,
    ),
]
CategoryIcon = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100,
        pattern=r"^i-ri-[a-z0-9-]+$",
    ),
]
CategoryTooltip = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=SUGGESTION_CATEGORY_TOOLTIP_MAX_LENGTH,
    ),
]


class SuggestionCategory(SQLModel, table=True):
    __tablename__ = "suggestion_category"
    __table_args__ = (
        UniqueConstraint("locale", "key", name="uq_suggestion_category_locale_key"),
    )

    id: ModelId
    locale: Annotated[SuggestionLocale, Field(sa_type=String(2), index=True)]
    key: str = Field(max_length=100)
    title: str = Field(max_length=255)
    description: str = Field(max_length=1_000)
    icon: str = Field(max_length=100)
    tooltip: str | None = Field(default=None, max_length=4_000)
    display_order: int = Field(default=0, ge=0)

    suggestions: list["PromptSuggestion"] = Relationship(back_populates="category")


class PromptSuggestion(SQLModel, table=True):
    __tablename__ = "prompt_suggestion"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "text", name="uq_prompt_suggestion_category_text"
        ),
    )

    id: ModelId
    category_id: uuid.UUID = Field(foreign_key="suggestion_category.id", index=True)
    text: str = Field(max_length=4_000)
    created_at: AutoDatetime
    updated_at: AutoDatetime
    created_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")
    archived_at: OptionalDatetime = Field(default=None, index=True)
    archived_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")

    category: SuggestionCategory | None = Relationship(back_populates="suggestions")


class SuggestionCreate(SQLModel):
    category_id: uuid.UUID
    text: SuggestionText


class SuggestionCategoryCreate(SQLModel):
    locale: SuggestionLocale
    title: CategoryTitle
    description: CategoryDescription
    icon: CategoryIcon
    tooltip: CategoryTooltip | None = None


class SuggestionArchiveUpdate(SQLModel):
    archived: bool


class PublicSuggestion(SQLModel):
    id: uuid.UUID
    text: str


class PublicSuggestionCategory(SQLModel):
    id: uuid.UUID
    key: str
    title: str
    description: str
    icon: str
    tooltip: str | None = None
    suggestions: list[PublicSuggestion]


class PublicSuggestionsResponse(SQLModel):
    categories: list[PublicSuggestionCategory]


class AdminSuggestion(SQLModel):
    id: uuid.UUID
    text: str
    locale: SuggestionLocale
    category_id: uuid.UUID
    category_title: str
    status: Literal["available", "archived"]
    created_at: datetime
    updated_at: datetime


class AdminSuggestionCategory(SQLModel):
    id: uuid.UUID
    locale: SuggestionLocale
    key: str
    title: str
    description: str
    icon: str
    tooltip: str | None = None
    display_order: int
