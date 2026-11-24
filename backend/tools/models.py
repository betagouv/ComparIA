import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Literal

if TYPE_CHECKING:
    from utils.database.models import Tool

logger = logging.getLogger("languia")

ToolStatus = Literal["success", "empty", "error"]


@dataclass(frozen=True)
class ToolResult:
    """What a tool hands back: text for the model, plus what to record."""

    content: str
    status: ToolStatus
    results: list[Any] = field(default_factory=list)

    @classmethod
    def error(cls, message: str) -> "ToolResult":
        return cls(
            content=json.dumps({"error": message}, ensure_ascii=False), status="error"
        )

    @classmethod
    def empty(cls, message: str) -> "ToolResult":
        return cls(
            content=json.dumps({"results": [], "message": message}, ensure_ascii=False),
            status="empty",
        )


@dataclass(frozen=True)
class ToolSpec:
    """One tool as the loop sees it."""

    name: str
    # OpenAI-style {"type": "function", "function": {...}} schema.
    schema: dict[str, Any]
    # Takes the raw JSON arguments string emitted by the model.
    run: Callable[[str], Awaitable[ToolResult]]
    # Shown to visitors. One MCP row exposes several functions under a single
    # label, so this cannot be derived from the name.
    label: str = ""
    # Key of the tool row this came from, so calls can be counted per tool.
    tool: str = ""

    def display_label(self) -> str:
        return self.label or self.name


def read_secret(row: "Tool") -> str | None:
    """
    The row's credential in clear, or None.

    A credential no configured key opens is treated as missing: the tool stops
    being offered rather than failing every call it would make.
    """
    from utils.secrets import SecretUnreadableError, decrypt_secret

    if not row.secret_encrypted:
        return None
    try:
        return decrypt_secret(row.secret_encrypted)
    except SecretUnreadableError:
        logger.error("The credential of tool '%s' cannot be decrypted", row.key)
        return None
