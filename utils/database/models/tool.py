from typing import Annotated, Literal

from sqlmodel import Field, String

from utils.validation import NonEmptyStr

from .utils import BaseDBModel

# How a tool is carried out. "builtin" names a function we ship; the key must
# exist in the arena's built-in registry. "mcp" points at a server whose
# functions are discovered by listing it.
ToolKind = Literal["builtin", "mcp"]

FIELDS = {
    "key": {
        "description": (
            "Stable identifier. For a built-in tool, the registry key "
            "(e.g. 'web_search')."
        )
    },
    "label": {"description": "Name shown to visitors, in French."},
    "description": {"description": "One line shown to visitors, in French."},
    "kind": {"description": "How the tool is carried out."},
    "url": {"description": "For an MCP tool, the server address."},
    "auth_header": {
        "description": (
            "For an MCP tool needing credentials, one header as 'Name: value'."
        )
    },
    "enabled": {
        "description": (
            "Disabled tools are never offered to a model nor shown to a visitor."
        )
    },
}


class ToolBase(BaseDBModel):
    key: Annotated[NonEmptyStr, Field(index=True, unique=True, **FIELDS["key"])]
    label: Annotated[NonEmptyStr, Field(**FIELDS["label"])]
    description: Annotated[str | None, Field(**FIELDS["description"])] = None
    kind: Annotated[ToolKind, Field(sa_type=String, **FIELDS["kind"])] = "builtin"
    url: Annotated[str | None, Field(**FIELDS["url"])] = None
    auth_header: Annotated[str | None, Field(**FIELDS["auth_header"])] = None
    enabled: Annotated[bool, Field(**FIELDS["enabled"])] = False


class Tool(ToolBase, table=True):
    """A tool the arena may offer to models, configured rather than declared."""

    __tablename__ = "tool"


class ToolUpsert(ToolBase):
    pass


class ToolPublic(ToolBase):
    pass
