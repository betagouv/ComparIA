import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.config import SelectionMode, TurnChoice
from backend.statistics.projection import Bucket
from utils.database.models.comparison import ArchivedReason, ErrorDetails

ActivityPeriod = Literal["24h", "7d", "30d", "90d", "365d", "all"]
ActivityBucket = Bucket
# What can keep a conversation out of the published dataset.
ActivityFlag = Literal["pii", "spam", "error", "archived", "not_analyzed"]


class ActivityFilters(BaseModel):
    """Filters shared by every view of the activity panel.

    `start` and `end` are both included, and replace `period` when either is
    set. Archived conversations are left out unless asked for, as on the
    public statistics page, so the two agree by default.
    """

    period: ActivityPeriod = "30d"
    start: date | None = None
    end: date | None = None
    mode: SelectionMode | None = None
    llm_id: uuid.UUID | None = None
    cohort: str | None = Field(default=None, max_length=100)
    include_archived: bool = False


class ConversationFilters(ActivityFilters):
    choice: TurnChoice | None = None
    has_vote: bool | None = None
    has_comment: bool | None = None
    revealed: bool | None = None
    category: str | None = Field(default=None, max_length=100)
    flag: ActivityFlag | None = None
    search: str | None = Field(default=None, min_length=3, max_length=200)
    # The last row of the previous page, as handed back in `next_cursor`.
    cursor: str | None = Field(default=None, max_length=100)
    limit: int = Field(default=50, ge=1, le=100)


class ActivityLLM(BaseModel):
    id: uuid.UUID
    name: str
    human_id: str


class ActivityFilterOptions(BaseModel):
    llms: list[ActivityLLM]
    cohorts: list[str]
    categories: list[str]


class ActivityTotals(BaseModel):
    conversations: int
    prompts: int
    # A turn with a choice other than "idk", as on the public statistics page.
    votes: int
    idk: int
    # Turns with a written comment, and turns with at least one tag.
    comments: int
    tagged: int
    voted_conversations: int
    revealed_conversations: int
    errored_conversations: int


class ActivityPoint(BaseModel):
    # "YYYY-MM-DD", or "YYYY-MM-DDTHH:00" for hourly buckets.
    date: str
    conversations: int
    prompts: int
    votes: int
    # The bucket still under way, with what it should hold once full. No
    # estimate this early in the bucket: see backend/statistics/projection.py.
    partial: bool = False
    projected_conversations: int | None = None
    projected_prompts: int | None = None
    projected_votes: int | None = None


class ActivityOverview(BaseModel):
    range_start: datetime | None
    range_end: datetime
    bucket: ActivityBucket
    totals: ActivityTotals
    activity: list[ActivityPoint]
    choices: dict[str, int]
    modes: dict[str, int]
    computed_at: datetime


class ActivityConversationRow(BaseModel):
    id: uuid.UUID
    created_at: datetime
    mode: str
    cohorts: str | None
    model_a: ActivityLLM | None
    model_b: ActivityLLM | None
    first_prompt: str
    turns: int
    choices: list[TurnChoice | None]
    # Tag keys across every prompt, per side, so the list can say which
    # answer was praised and which was criticised.
    tags_a: list[str]
    tags_b: list[str]
    has_comment: bool
    # The first comment left, cut short: enough to skim, the rest is one click.
    comment: str | None
    revealed: bool
    categories: list[str]
    llm_analyzed: bool
    contains_pii: bool
    contains_spam: bool
    archived: bool
    has_error: bool


class ActivityConversationsPage(BaseModel):
    items: list[ActivityConversationRow]
    next_cursor: str | None
    # Only on the first page, and counted up to TOTAL_CAP: past that the
    # number costs a full scan and tells an admin nothing more.
    total: int | None
    total_capped: bool


class ActivityAnswer(BaseModel):
    content: str
    reasoning_content: str | None
    tokens: int | None
    duration_ms: int | None


class ActivityPromptCheck(BaseModel):
    decision: str
    model: str
    triggered: dict[str, str]
    user_proceeded: bool


class ActivityTurn(BaseModel):
    id: uuid.UUID
    created_at: datetime
    prompt: str
    web_search_results: list[dict] | None
    answer_a: ActivityAnswer | None
    answer_b: ActivityAnswer | None
    choice: TurnChoice | None
    voted_at: datetime | None
    tags_a: list[str]
    tags_b: list[str]
    comment_a: str | None
    comment_b: str | None
    prompt_check: ActivityPromptCheck | None


class ActivityConversation(BaseModel):
    id: uuid.UUID
    created_at: datetime
    mode: str
    cohorts: str | None
    revealed: bool
    revealed_at: datetime | None
    model_a: ActivityLLM | None
    model_b: ActivityLLM | None
    system_msg_a: str | None
    system_msg_b: str | None
    llm_analyzed: bool
    short_summary: str | None
    keywords: list[str]
    categories: list[str]
    languages: list[str]
    contains_pii: bool
    contains_spam: bool
    archived: bool
    archived_reason: ArchivedReason | None
    error: ErrorDetails | None
    turns: list[ActivityTurn]
