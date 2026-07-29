from typing import Annotated, Literal

from sqlmodel import Field, String

from utils.validation import NonEmptyStr

from .utils import BaseDBModel

# How a tool is carried out. "builtin" names a function we ship; the key must
# exist in the arena's built-in registry.
ToolKind = Literal["builtin"]

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
    enabled: Annotated[bool, Field(**FIELDS["enabled"])] = False


class Tool(ToolBase, table=True):
    """A tool the arena may offer to models, configured rather than declared."""

    __tablename__ = "tool"


class ToolUpsert(ToolBase):
    pass


class ToolPublic(ToolBase):
    pass
