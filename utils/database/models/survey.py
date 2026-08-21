import unicodedata
import uuid
from typing import Annotated, Literal, get_args

from pydantic import StringConstraints, field_validator
from sqlalchemy import Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from .utils import BaseDBModel, OptionalDatetime, UtcDatetime

# Where a question is put to the visitor. A question carries a set of these,
# so the same question can be asked in both places: whoever answers it first
# is not asked again, whichever moment that was.
#  - 'signup' puts it on the sign-in form. Only means anything on an instance
#    running AUTH_ACCESS_POLICY=sign_in_required, since anywhere else the
#    visitor can simply not create an account. Whether it blocks that account
#    is 'required', not the moment.
#  - 'after_vote' puts it in a popup on the reveal page, always dismissible
#    and capped at MAX_QUESTION_PROMPTS showings.
SurveyTrigger = Literal["signup", "after_vote"]
SURVEY_TRIGGERS: tuple[SurveyTrigger, ...] = get_args(SurveyTrigger)

# Closed answers only. Free text is where people type their employer, their
# town or their name, and published rows carry the prompt text alongside, so
# an 'other, please specify' box is a re-identification vector for the sake of
# a long tail nobody analyses. An admin who needs 'other' adds it as an option.
SurveyInputType = Literal["select", "checkbox_group"]
SURVEY_INPUT_TYPES: tuple[SurveyInputType, ...] = get_args(SurveyInputType)

# How many times one question may be put to the same respondent before it goes
# quiet for good. Expecting an answer on the first showing is optimistic; a
# fourth showing is nagging.
MAX_QUESTION_PROMPTS = 3

# Questions shown in a single after-vote popup. Past three the popup stops
# reading as a question and starts reading as a form.
MAX_QUESTIONS_PER_PROMPT = 3

# How many question ids one dismiss call may name. The client only ever sends
# what one popup showed; anything longer is a bug or abuse, and the log rows
# it would create are worthless either way.
MAX_DISMISS_IDS = 50

QuestionLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)
]
OptionLabel = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class SurveyOption(SQLModel):
    """
    One choice, stored inside the question's 'options' JSONB rather than in a
    table of its own. Options are only ever read through their question, so a
    second table would buy joins and nothing else.
    """

    # Derived from the label on creation and never updated afterwards: it is
    # the value stored in an answer and published in the dataset. Renaming the
    # label is free, renaming the key would silently split a column in two.
    key: Annotated[str, Field(max_length=100)]
    labels: dict[str, str]
    # Removing an option archives it. Answers already given keep resolving,
    # and the option stops being offered.
    archived: bool = False


class SurveyQuestionBase(BaseDBModel):
    # Derived from the first label on creation, immutable thereafter. The
    # question keeps its identity across edits, so rewording 'Gender' into
    # 'Gender identity' does not start a new column in the dataset.
    key: Annotated[str, Field(max_length=100, unique=True, index=True)]
    # At least one moment, kept as a list rather than a column per moment:
    # nothing filters on it in SQL, the whole question list is cached and
    # filtered in Python, and one column stays honest as moments are added.
    triggers: Annotated[list[SurveyTrigger], Field(sa_type=JSONB)]
    # Whether an unanswered question blocks account creation. Only the signup
    # moment reads it: the after-vote popup is dismissible by design, so a
    # question asked in both places blocks the form and not the popup.
    required: bool = Field(default=True)
    input_type: Annotated[SurveyInputType, Field(sa_type=String)]
    # Per-locale question text, {'fr': "Quelle est votre tranche d'age ?"}.
    labels: Annotated[dict[str, str], Field(sa_type=JSONB)]
    options: Annotated[list[dict], Field(sa_type=JSONB)]
    # Whether answers reach the published dataset. Off by default: an admin
    # adding a question for internal segmentation should not have to know the
    # export pipeline exists, so the risky direction takes a deliberate click.
    published: bool = Field(default=False)
    # Bumped whenever the wording or the option set changes, and stamped onto
    # every answer. Editing in place is what the admins asked for, and this is
    # what keeps 'this column means two things after March' visible in the data
    # rather than invisible.
    revision: int = Field(default=1, ge=1)
    # One rank across every question, not one per moment: a question can sit
    # in both moments, and each moment shows its own subset in this order.
    display_order: int = Field(default=0, ge=0)
    archived_at: OptionalDatetime = Field(default=None, index=True)
    archived_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")


class SurveyQuestion(SurveyQuestionBase, table=True):
    __tablename__ = "survey_question"


class SurveyAnswerBase(BaseDBModel):
    question_id: uuid.UUID = Field(foreign_key="survey_question.id", index=True)
    option_key: Annotated[str, Field(max_length=100)]
    # Exactly one of the two is set, mirroring how 'comparison' carries
    # ownership. Anonymous visitors are the bulk of an anonymous_first
    # instance, and excluding them would describe only the users committed
    # enough to hold an account.
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="auth_user.id", index=True
    )
    anonymous_user_hash: str | None = Field(default=None, index=True)
    # The wording this person actually answered under.
    question_revision: int = Field(default=1, ge=1)
    # The participation terms in force when the answer was given. There is one
    # consent, not a separate survey one, so this is the record of what the
    # respondent was told, and the filter deciding what may be published.
    terms_version: str | None = Field(default=None)
    answered_at: UtcDatetime


class SurveyAnswer(SurveyAnswerBase, table=True):
    __tablename__ = "survey_answer"

    # One row per option per respondent, enforced by the database rather than
    # only by delete-then-insert in `submit_answers`: two concurrent
    # submissions would otherwise both pass the delete and leave a duplicate.
    # Both ownership columns are nullable and Postgres treats NULL as distinct
    # in unique indexes, so each is wrapped in COALESCE to a sentinel that no
    # real row carries — exactly one of the two is ever set.
    __table_args__ = (
        Index(
            "uq_survey_answer_respondent_option",
            "question_id",
            "option_key",
            text("COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid)"),
            text("COALESCE(anonymous_user_hash, '')"),
            unique=True,
        ),
    )


class SurveyPromptLogBase(BaseDBModel):
    """
    One row per question per respondent, written when the question is shown.
    A question that was shown and not answered leaves no answer row, so the
    re-ask rules need somewhere else to count from.
    """

    question_id: uuid.UUID = Field(foreign_key="survey_question.id", index=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="auth_user.id", index=True
    )
    anonymous_user_hash: str | None = Field(default=None, index=True)
    shown_count: int = Field(default=0, ge=0)
    last_shown_at: UtcDatetime


class SurveyPromptLog(SurveyPromptLogBase, table=True):
    __tablename__ = "survey_prompt_log"


# --- public shapes, served to the arena ---------------------------------


class PublicSurveyOption(SQLModel):
    key: str
    label: str


class PublicSurveyQuestion(SQLModel):
    id: uuid.UUID
    key: str
    # The moments are not sent: the caller asked for one, and the form only
    # needs to know whether it may be submitted without an answer.
    required: bool
    input_type: SurveyInputType
    label: str
    revision: int
    options: list[PublicSurveyOption]


class PublicSurveyQuestionsResponse(SQLModel):
    questions: list[PublicSurveyQuestion]


class SurveyQuestionAnswer(SQLModel):
    question_id: uuid.UUID
    # One key for 'select', any number for 'checkbox_group'. An empty list
    # clears the answer, which is how the profile page removes one.
    option_keys: list[str]


class SurveyAnswerSubmit(SQLModel):
    answers: list[SurveyQuestionAnswer]


class SurveyDismiss(SQLModel):
    """
    Closing the popup and declining it are the same thing: both count as one
    of the three showings and neither is a special case worth a column.
    """

    question_ids: list[uuid.UUID]


class MySurveyAnswer(SQLModel):
    """What the profile page and the personal-data export show."""

    question_id: uuid.UUID
    question_key: str
    label: str
    input_type: SurveyInputType
    options: list[PublicSurveyOption]
    selected_keys: list[str]


class MySurveyAnswersResponse(SQLModel):
    answers: list[MySurveyAnswer]


# --- admin shapes -------------------------------------------------------


def _no_control_chars(value: str) -> str:
    if any(unicodedata.category(char) == "Cc" for char in value):
        raise ValueError("label cannot contain control characters")
    return value


def _validate_labels(value: dict[str, str], what: str) -> dict[str, str]:
    if not value:
        raise ValueError(f"a {what} needs at least one label")
    for label in value.values():
        _no_control_chars(label)
    return value


def _validate_triggers(value: list[SurveyTrigger]) -> list[SurveyTrigger]:
    if not value:
        raise ValueError("a question needs at least one moment")
    if len(value) != len(set(value)):
        raise ValueError("a moment cannot appear twice")
    return value


def _validate_options(value: list["SurveyOptionWrite"]) -> list["SurveyOptionWrite"]:
    live = [option for option in value if not option.archived]
    if len(live) < 2:
        raise ValueError("a question needs at least two options")
    keys = [option.key for option in value if option.key]
    if len(keys) != len(set(keys)):
        raise ValueError("an option key cannot appear twice")
    return value


class SurveyOptionWrite(SQLModel):
    # Absent when the admin adds a new option, present when they edit one that
    # already exists. Sending it back is what keeps the key, and every answer
    # pointing at it, attached to the row the admin is editing.
    key: str | None = None
    labels: dict[str, OptionLabel]
    archived: bool = False

    @field_validator("labels")
    @classmethod
    def check_labels(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_labels(value, "option")


class SurveyQuestionCreate(SQLModel):
    triggers: list[SurveyTrigger]
    required: bool = True
    input_type: SurveyInputType
    # One entry per language the instance serves. The key is derived from the
    # first label given, so at least one is required.
    labels: dict[str, QuestionLabel]
    options: list[SurveyOptionWrite]
    published: bool = False

    @field_validator("labels")
    @classmethod
    def check_labels(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_labels(value, "question")

    @field_validator("triggers")
    @classmethod
    def check_triggers(cls, value: list[SurveyTrigger]) -> list[SurveyTrigger]:
        return _validate_triggers(value)

    @field_validator("options")
    @classmethod
    def check_options(cls, value: list[SurveyOptionWrite]) -> list[SurveyOptionWrite]:
        return _validate_options(value)


class SurveyQuestionUpdate(SQLModel):
    # Editable, unlike input_type: moving a question to another moment, or
    # adding one, changes nothing about the answers already given.
    triggers: list[SurveyTrigger]
    required: bool
    labels: dict[str, QuestionLabel]
    options: list[SurveyOptionWrite]
    published: bool

    @field_validator("labels")
    @classmethod
    def check_labels(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_labels(value, "question")

    @field_validator("triggers")
    @classmethod
    def check_triggers(cls, value: list[SurveyTrigger]) -> list[SurveyTrigger]:
        return _validate_triggers(value)

    @field_validator("options")
    @classmethod
    def check_options(cls, value: list[SurveyOptionWrite]) -> list[SurveyOptionWrite]:
        return _validate_options(value)


class SurveyQuestionArchiveUpdate(SQLModel):
    archived: bool


class SurveyQuestionOrder(SQLModel):
    """
    The whole order, written in one request, as the vote tags do: one round
    trip per drag, and the gaps archiving leaves in 'display_order' get
    rewritten away.
    """

    ids: list[uuid.UUID]


class AdminSurveyOption(SQLModel):
    key: str
    labels: dict[str, str]
    archived: bool
    # How many answers already carry this key.
    answer_count: int


class AdminSurveyQuestion(SQLModel):
    id: uuid.UUID
    key: str
    triggers: list[SurveyTrigger]
    required: bool
    input_type: SurveyInputType
    labels: dict[str, str]
    options: list[AdminSurveyOption]
    published: bool
    revision: int
    display_order: int
    archived: bool
    respondent_count: int


class AdminSurveyResponse(SQLModel):
    questions: list[AdminSurveyQuestion]
    total_respondents: int
