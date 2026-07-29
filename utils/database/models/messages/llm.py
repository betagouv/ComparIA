from datetime import datetime
from typing import Annotated, Any, Literal

from linkup import LinkupSearchTextResult
from pydantic import BaseModel, ConfigDict
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from utils.validation import StripAndEmptyAsNone

from ..utils import ModelId, OptionalDatetime


class AgentTraceReasoning(BaseModel):
    type: Literal["reasoning"] = "reasoning"
    content: str


class AgentTraceIntermediateContent(BaseModel):
    type: Literal["intermediate_content"] = "intermediate_content"
    content: str


class AgentTraceToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str
    name: str
    # Readable name of the tool the visitor selected. One MCP row exposes
    # several functions, so the interface cannot derive it from `name`.
    label: str = ""
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


class AgentTraceToolResult(BaseModel):
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

# Why the model stopped using tools. "completed" means it decided it was done;
# every other value means we cut it off, and the difference matters when reading
# tool-use behaviour out of the data.
AgentStopReason = Literal[
    "completed", "deadline", "call_limit", "round_limit", "context_exceeded"
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
    web_search_results: Annotated[
        list[LinkupSearchTextResult] | None, Field(sa_type=JSONB)
    ] = None
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


class LLMMessageCreate(LLMMessageBase):
    content: str = ""
    # Nullable: StripAndEmptyAsNone persists empty reasoning_content as NULL,
    # so DB-loaded rows must validate back through LLMMessageCreate.
    reasoning_content: str | None = ""


class LLMMessageRead(LLMMessageFinal):
    pass
