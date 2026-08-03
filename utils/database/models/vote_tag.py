import uuid
from typing import Annotated, Literal, get_args

from pydantic import StringConstraints, field_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from .utils import BaseDBModel, OptionalDatetime

VoteTagSign = Literal["positive", "negative"]
VOTE_TAG_SIGNS: tuple[VoteTagSign, ...] = get_args(VoteTagSign)

# The tags every instance ships with. They are seeded as reserved rows, keep
# these keys forever and stay comparable across published datasets. Their
# labels live in the translation files under 'vote.choices.{sign}.{key}', so
# they are absent from the 'labels' column.
RESERVED_POSITIVE_KEYS: tuple[str, ...] = (
    "useful",
    "complete",
    "creative",
    "clear_formatting",
)
RESERVED_NEGATIVE_KEYS: tuple[str, ...] = (
    "incorrect",
    "superficial",
    "instructions_not_followed",
)
RESERVED_KEYS: tuple[str, ...] = RESERVED_POSITIVE_KEYS + RESERVED_NEGATIVE_KEYS


class VoteTagBase(BaseDBModel):
    # Derived from the label on creation and never updated afterwards: it is
    # the value stored in a vote and published in the dataset.
    key: Annotated[str, Field(max_length=100, unique=True, index=True)]
    sign: Annotated[VoteTagSign, Field(sa_type=String)]
    emoji: str = Field(max_length=16)
    reserved: bool = Field(default=False)
    # Per-locale labels, {'fr': 'Bien sourcee'}. Null for reserved tags, which
    # read their label from the translation files instead.
    labels: Annotated[dict[str, str] | None, Field(sa_type=JSONB)] = None
    display_order: int = Field(default=0, ge=0)
    archived_at: OptionalDatetime = Field(default=None, index=True)
    archived_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")


class VoteTag(VoteTagBase, table=True):
    __tablename__ = "vote_tag"


class PublicVoteTag(SQLModel):
    key: str
    sign: VoteTagSign
    emoji: str
    reserved: bool
    label: str | None = None


class PublicVoteTagsResponse(SQLModel):
    tags: list[PublicVoteTag]


TagEmoji = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)
]
TagLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class VoteTagCreate(SQLModel):
    sign: VoteTagSign
    emoji: TagEmoji
    # One entry per language the instance serves. The key is derived from the
    # first label given, so at least one is required.
    labels: dict[str, TagLabel]

    @field_validator("labels")
    @classmethod
    def at_least_one_label(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("a tag needs at least one label")
        return value


class VoteTagUpdate(SQLModel):
    emoji: TagEmoji
    labels: dict[str, TagLabel]

    @field_validator("labels")
    @classmethod
    def at_least_one_label(cls, value: dict[str, str]) -> dict[str, str]:
        if not value:
            raise ValueError("a tag needs at least one label")
        return value


class VoteTagArchiveUpdate(SQLModel):
    archived: bool


class VoteTagMove(SQLModel):
    direction: Literal["up", "down"]


class AdminVoteTag(SQLModel):
    id: uuid.UUID
    key: str
    sign: VoteTagSign
    emoji: str
    reserved: bool
    labels: dict[str, str] | None
    display_order: int
    archived: bool
    # How many votes already carry this key. A tag nobody used can be deleted
    # outright; once it is in the data, removing it archives instead.
    usage_count: int


class AdminVoteTagsResponse(SQLModel):
    tags: list[AdminVoteTag]
