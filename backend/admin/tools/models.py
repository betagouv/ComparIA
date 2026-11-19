from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from utils.database.models import ToolKind

# Why a test failed, as a key the panel translates. Provider messages are
# not passed on: they can carry the credential back to the browser.
ToolTestError = Literal[
    "no_credential",
    "no_url",
    "invalid_credential",
    "no_credit",
    "unreachable",
    "timeout",
    "unknown_builtin",
]


class ToolFunction(BaseModel):
    name: str
    description: str = ""


class ToolTestResult(BaseModel):
    ok: bool
    error: ToolTestError | None = None
    # What an MCP server lists, so the panel can offer them as an allowlist.
    functions: list[ToolFunction] | None = None


class ToolDraft(BaseModel):
    """A tool being set up, tested before it is saved."""

    kind: ToolKind
    key: str = ""
    url: str | None = None
    secret: str | None = None


class ToolSwitch(BaseModel):
    enabled: bool


class ToolHealth(BaseModel):
    id: UUID
    ok: bool
    error: ToolTestError | None = None
    checked_at: datetime


class ToolUsage(BaseModel):
    id: UUID
    # Calls models made over TOOL_USAGE_DAYS, and how many failed.
    calls: int = 0
    failures: int = 0
