from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BeforeValidator,
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
)
from sqlmodel import SQLModel

from backend.config import CustomModelsSelection, SelectionMode, TurnChoice
from utils.database.models import (
    ArchivedReason,
    BotPos,
    ErrorDetails,
    LLMMessageFinal,
    SystemMessageRead,
    UserMessageRead,
)

Datasets = Literal["normal", "raw"]


class DatasetTurnMetadata(SQLModel):
    # FIXME all those shouldn't be None?
    tokens_a: int | None
    tokens_b: int | None
    conso_a: float | None  # None for legacy comparisons with empty llm_id
    conso_b: float | None  # None for legacy comparisons with empty llm_id
    duration_a: float | None
    duration_b: float | None
    latency_a: float | None
    latency_b: float | None


class DatasetComparisonBaseMetadata(SQLModel):
    mode: SelectionMode
    custom_models_selection: CustomModelsSelection
    categories: list[str] | None
    languages: list[str] | None
    short_summary: str | None


class DatasetComparisonMetadata(DatasetComparisonBaseMetadata):
    # FIXME all those shouldn't be None?
    total_tokens_a: int | None
    total_tokens_b: int | None
    total_conso_a: float | None  # None for legacy comparisons with empty llm_id
    total_conso_b: float | None  # None for legacy comparisons with empty llm_id


class DatasetComparisonExtraMetadata(SQLModel):
    cohorts: str | None
    error: ErrorDetails | None
    llm_analyzed: bool | None = None
    contains_pii: bool | None = None
    contains_spam: bool | None = None
    archived: bool | None = None
    archived_reason: ArchivedReason | None
    archived_at: datetime | None


class DatasetTurn(SQLModel):
    """
    Actual Turn data
    Merged with shared DatasetComparison
    """

    response_id: Annotated[str, BeforeValidator(str), Field(validation_alias="id")]
    choice: TurnChoice | None  # FIXME should not

    # Excluded, used to compute responses
    user_msg: Annotated[UserMessageRead, Field(exclude=True)]
    llm_msg_a: Annotated[
        LLMMessageFinal | None, Field(exclude=True)
    ]  # FIXME shouldn't be None?
    llm_msg_b: Annotated[
        LLMMessageFinal | None, Field(exclude=True)
    ]  # FIXME shouldn't be None?

    # Extracted then merged with DatasetComparisonMetadata
    metadata_: Annotated[
        DatasetTurnMetadata, Field(default=None, validate_default=True)
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def response_a(self) -> list[dict]:
        return self.parse_response("a")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def response_b(self) -> list[dict]:
        return self.parse_response("b")

    @field_validator("metadata_", mode="before")
    @classmethod
    def parse_metadata(cls, value: None, info: ValidationInfo) -> dict:
        assert info.context
        llm_a = info.context["llm_a"]
        msg_a = info.data.get("llm_msg_a")  # FIXME shouldn't be None?
        llm_b = info.context["llm_b"]
        msg_b = info.data.get("llm_msg_b")  # FIXME shouldn't be None?

        # FIXME all next shouldn't be None?
        return {
            "tokens_a": msg_a.tokens if msg_a else None,
            "tokens_b": msg_b.tokens if msg_b else None,
            "conso_a": (
                (llm_a.wh_per_million_token / 1_000_000) * msg_a.tokens / 1_000
                if (llm_a and msg_a)
                else None
            ),
            "conso_b": (
                (llm_b.wh_per_million_token / 1_000_000) * msg_b.tokens / 1_000
                if (llm_b and msg_b)
                else None
            ),
            "latency_a": (
                (msg_a.responded_at - msg_a.created_at).total_seconds()
                if msg_a
                else None
            ),
            "latency_b": (
                (msg_b.responded_at - msg_b.created_at).total_seconds()
                if msg_b
                else None
            ),
            "duration_a": (
                (msg_a.updated_at - msg_a.responded_at).total_seconds()
                if msg_a
                else None
            ),
            "duration_b": (
                (msg_b.updated_at - msg_b.responded_at).total_seconds()
                if msg_b
                else None
            ),
        }

    # HELPERS

    def parse_response(self, side: BotPos) -> list[dict]:
        msgs = [
            self.user_msg.model_dump(
                include={"role", "content", "user_content"},
                context={"merge_web_search": True},
            )
        ]
        if llm_msg := getattr(self, f"llm_msg_{side}"):
            msgs.append(
                llm_msg.model_dump(include={"role", "content", "reasoning_content"})
            )
        return msgs


class DatasetComparison(SQLModel):
    # Excluded, used to compute full conversations
    system_msg_a: Annotated[SystemMessageRead | None, Field(exclude=True)]
    system_msg_b: Annotated[SystemMessageRead | None, Field(exclude=True)]

    # Actual data
    comparison_id: Annotated[str, BeforeValidator(str), Field(validation_alias="id")]
    model_a: Annotated[str, Field(validation_alias="llm_id_a")]
    model_b: Annotated[str, Field(validation_alias="llm_id_b")]

    # Extracted to build rows
    turns_: Annotated[list[DatasetTurn], Field(validation_alias="turns")]
    metadata_: Annotated[
        DatasetComparisonMetadata, Field(default=None, validate_default=True)
    ]
    extra_metadata_: Annotated[
        DatasetComparisonExtraMetadata, Field(default=None, validate_default=True)
    ]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def full_conversation_a(self) -> list[dict]:
        return self.parse_full_conversation("a")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def full_conversation_b(self) -> list[dict]:
        return self.parse_full_conversation("b")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def excluded(self) -> bool:
        if any(
            [
                bool(self.extra_metadata_.cohorts),
                self.extra_metadata_.archived is not False,
                self.extra_metadata_.error is not None,
                self.extra_metadata_.llm_analyzed is not True,
            ]
        ):
            return True
        return False

    @field_validator("metadata_", mode="before")
    @classmethod
    def parse_metadata(cls, value: None, info: ValidationInfo) -> dict:
        assert info.context
        turns_metadata = [turn.metadata_ for turn in info.data["turns_"]]

        return {
            **info.context["metadata"],
            # FIXME all next shouldn't be None?
            "total_tokens_a": (
                sum(
                    meta.tokens_a
                    for meta in turns_metadata
                    if meta.tokens_a is not None
                )
                if all(meta.tokens_a is not None for meta in turns_metadata)
                else None
            ),
            "total_tokens_b": (
                sum(
                    meta.tokens_b
                    for meta in turns_metadata
                    if meta.tokens_b is not None
                )
                if all(meta.tokens_b is not None for meta in turns_metadata)
                else None
            ),
            "total_conso_a": (
                sum(meta.conso_a for meta in turns_metadata)
                if all(meta.conso_a is not None for meta in turns_metadata)
                else None
            ),
            "total_conso_b": (
                sum(meta.conso_b for meta in turns_metadata)
                if all(meta.conso_b is not None for meta in turns_metadata)
                else None
            ),
        }

    @field_validator("extra_metadata_", mode="before")
    @classmethod
    def parse_extra_metadata(cls, value: None, info: ValidationInfo) -> dict:
        assert info.context
        return info.context["extra_metadata"]

    # HELPERS

    def parse_full_conversation(self, side: BotPos) -> list[dict]:
        conversation = []
        if system_msg := getattr(self, f"system_msg_{side}"):
            conversation.append(system_msg.model_dump(include={"role", "content"}))
        for turn in self.turns_:
            conversation += getattr(turn, f"response_{side}")
        return conversation
