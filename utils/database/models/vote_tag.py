import uuid
from typing import Annotated, Literal, get_args

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
