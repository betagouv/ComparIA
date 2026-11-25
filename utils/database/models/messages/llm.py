from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from utils.validation import StripAndEmptyAsNone

from ..utils import ModelId, OptionalDatetime


class AgentTraceReasoning(BaseModel, extra="forbid"):
    type: Literal["reasoning"] = "reasoning"
    content: str


class AgentTraceIntermediateContent(BaseModel, extra="forbid"):
    type: Literal["intermediate_content"] = "intermediate_content"
    content: str


class AgentTraceToolCall(BaseModel, extra="forbid"):
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    name: str
    # Readable name of the tool the visitor selected. One MCP row exposes
    # several functions, so the interface cannot derive it from `name`.
    label: str = ""
    # Key of the tool row. Labels can be renamed; this is what usage counts
    # are kept by. Empty on calls recorded before it existed.
    tool: str = ""
    arguments_json: str
    arguments: dict[str, Any] | None = None


class ToolSource(BaseModel):
    """
    One piece of evidence a tool handed back.

    Deliberately not Linkup's shape: an MCP server returns text with no address,
    and the trace has to hold both. Reads back the rows written before this
    existed, whose extra Linkup fields are simply ignored.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str = ""
    url: str | None = None
    content: str = ""
    favicon: str | None = None


class AgentTraceToolResult(BaseModel, extra="forbid"):
    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str
    name: str
    status: Literal["success", "empty", "error"]
    duration_ms: int
    content: str
    results: list[ToolSource] = []


AgentTraceEvent = (
    AgentTraceReasoning
    | AgentTraceIntermediateContent
    | AgentTraceToolCall
    | AgentTraceToolResult
)


AgentTraceInput = list[dict[str, Any]] | list[AgentTraceEvent] | None


def _trace_events(agent_trace: AgentTraceInput) -> list[dict[str, Any]]:
    """The trace as stored (plain dicts) or as models, read as dicts."""
    return [
        event if isinstance(event, dict) else event.model_dump()
        for event in agent_trace or []
    ]


def tool_evidence(
    agent_trace: AgentTraceInput,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """What a model searched for and what its tools handed back, as published.

    The dataset export and the check that screens it before publication both
    read this, so nothing reaches the dataset that the check did not read.
    """
    events = _trace_events(agent_trace)
    queries = [
        {"name": event["name"], "arguments": event["arguments_json"]}
        for event in events
        if event.get("type") == "tool_call"
    ]
    sources = [
        source
        for event in events
        if event.get("type") == "tool_result"
        for source in event.get("results") or []
    ]
    return queries, sources


def published_answer(content: str | None, agent_trace: AgentTraceInput) -> str | None:
    """The answer as the visitor read it, as published.

    Text a model writes before calling a tool leaves `content` for the trace,
    where the interface shows it between the tool steps. The dataset and the
    check that screens it put it back, in order, ahead of the final answer.
    """
    parts = [
        event["content"]
        for event in _trace_events(agent_trace)
        if event.get("type") == "intermediate_content"
    ]
    if not parts:
        return content
    return "\n\n".join(part.strip() for part in [*parts, content or ""] if part.strip())


# Why the model stopped using tools. "completed" means it decided it was done;
# every other value means we cut it off, and the difference matters when reading
# tool-use behaviour out of the data.
AgentStopReason = Literal[
    "completed",
    "deadline",
    "call_limit",
    "round_limit",
    "context_exceeded",
    "repeat_limit",
]


class LLMMessageBase(SQLModel):
    id: ModelId
    role: Annotated[Literal["assistant"], Field(sa_type=String)] = "assistant"
    created_at: OptionalDatetime = None
    responded_at: OptionalDatetime = None
    updated_at: OptionalDatetime = None

    content: str
    reasoning_content: str | None = None

    generation_id: str | None = None
    tokens: int | None = None
    is_cached: bool = False
    agent_trace: Annotated[list[AgentTraceEvent] | None, Field(sa_type=JSONB)] = None
    agent_stop_reason: Annotated[AgentStopReason | None, Field(sa_type=String)] = None


class LLMMessageFinal(LLMMessageBase):
    created_at: datetime
    responded_at: datetime
    updated_at: datetime
    content: Annotated[str, StripAndEmptyAsNone]
    reasoning_content: Annotated[str | None, StripAndEmptyAsNone]

    generation_id: str
    tokens: int
    is_cached: bool


class LLMMessage(LLMMessageFinal, table=True):
    __tablename__ = "llm_message"
    # The admin tools list counts calls over recent days. Only messages with
    # a trace hold any, so the index covers those alone and stays small.
    __table_args__ = (
        Index(
            "ix_llm_message_traced_created_at",
            "created_at",
            postgresql_where=text("jsonb_typeof(agent_trace) = 'array'"),
        ),
    )


class LLMMessageCreate(LLMMessageBase):
    content: str = ""
    # Nullable: StripAndEmptyAsNone persists empty reasoning_content as NULL,
    # so DB-loaded rows must validate back through LLMMessageCreate.
    reasoning_content: str | None = ""

    # This is the shape the browser sees, on every streamed chunk and again in
    # TurnPublic, so these three stay server-side: the provider's own id
    # prefixes name the provider, and the token count and cache hit are
    # per-model tells. They are still set and still saved, only not sent.
    # Reveal reports the token counts once the vote is in.
    generation_id: str | None = Field(default=None, exclude=True)
    tokens: int | None = Field(default=None, exclude=True)
    is_cached: bool = Field(default=False, exclude=True)


class LLMMessageRead(LLMMessageFinal):
    pass
