import re
from typing import Annotated, Literal

from pydantic import StringConstraints, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, String

from utils.i18n import TranslatableRaw
from utils.validation import NonEmptyStr

from .utils import BaseDBModel, logo_version

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
    "label": {"description": "Name shown to visitors, in each language."},
    "description": {"description": "One line shown to visitors, in each language."},
    "kind": {"description": "How the tool is carried out."},
    "url": {"description": "For an MCP tool, the server address."},
    "allowed_functions": {
        "description": (
            "For an MCP tool, the server functions offered to models. "
            "Leave empty to offer every function the server lists."
        )
    },
    "allowed_domains": {
        "description": (
            "For web search, the only sites results may come from "
            "(e.g. 'service-public.fr'). Leave empty for the whole web."
        )
    },
    "blocked_domains": {
        "description": (
            "For web search, sites results never come from. Cannot be "
            "combined with allowed domains."
        )
    },
    "enabled": {
        "description": (
            "Disabled tools are never offered to a model nor in the visitor "
            "picker. Their name and logo still label past comparisons."
        )
    },
    "secret": {
        "title": "Credential",
        "description": (
            "For a built-in tool, its provider API key. For an MCP tool, a "
            "token sent as 'Authorization: Bearer', or a whole header as "
            "'Name: value'. Stored encrypted and never shown again."
        ),
    },
}

# A plain host name, the shape Linkup's domain filters accept.
_DOMAIN = re.compile(r"^(?=.{1,253}$)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$")


def _normalize_domain(value: str) -> str:
    """Accept what an admin is likely to paste: a URL or a bare host."""
    domain = value.strip().lower()
    domain = re.sub(r"^[a-z]+://", "", domain).split("/", 1)[0]
    domain = domain.removeprefix("www.")
    if not _DOMAIN.match(domain):
        raise PydanticCustomError(
            "invalid_domain", "'{value}' is not a domain name.", {"value": value}
        )
    return domain


class ToolBase(BaseDBModel):
    key: Annotated[NonEmptyStr, Field(index=True, unique=True, **FIELDS["key"])]
    label: Annotated[TranslatableRaw[str], Field(sa_type=JSONB, **FIELDS["label"])]
    description: Annotated[
        TranslatableRaw[str] | None, Field(sa_type=JSONB, **FIELDS["description"])
    ] = None
    kind: Annotated[ToolKind, Field(sa_type=String, **FIELDS["kind"])] = "builtin"
    url: Annotated[str | None, Field(**FIELDS["url"])] = None
    allowed_functions: Annotated[
        list[str] | None, Field(sa_type=JSONB, **FIELDS["allowed_functions"])
    ] = None
    allowed_domains: Annotated[
        list[str] | None, Field(sa_type=JSONB, **FIELDS["allowed_domains"])
    ] = None
    blocked_domains: Annotated[
        list[str] | None, Field(sa_type=JSONB, **FIELDS["blocked_domains"])
    ] = None
    enabled: Annotated[bool, Field(**FIELDS["enabled"])] = False


class Tool(ToolBase, table=True):
    """A tool the arena may offer to models, configured rather than declared."""

    __tablename__ = "tool"

    # Fernet token from utils.secrets. Only the arena reads it back, at the
    # moment it calls the provider or the server.
    secret_encrypted: str | None = None

    logo: Annotated[bytes | None, Field(sa_type=LargeBinary)] = None
    logo_content_type: str | None = None

    @property
    def logo_url(self) -> str | None:
        if self.logo:
            return f"/tools/logo/{self.id}?v={logo_version(self.logo)}"
        return None


# The picker lists tools in a narrow menu. Longer text wraps and pushes the
# other entries down. Set on writes only, so rows saved before the limit load.
ToolLabel = Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)]
ToolDescription = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=70)
]


class ToolUpsert(ToolBase):
    label: Annotated[TranslatableRaw[ToolLabel], Field(**FIELDS["label"])]
    description: Annotated[
        TranslatableRaw[ToolDescription] | None, Field(**FIELDS["description"])
    ] = None
    # Write-only: left empty, the stored credential is kept. Removing it has
    # its own route, so that clearing the field by accident never does.
    secret: Annotated[str | None, Field(**FIELDS["secret"])] = None

    @model_validator(mode="after")
    def check_lists(self):
        """Drop blank entries, normalise domains, refuse both domain lists."""
        self.label = {locale: text for locale, text in self.label.items() if text}
        if not self.label:
            raise PydanticCustomError("label_required", "Name the tool.")
        if self.description is not None:
            self.description = {
                locale: text for locale, text in self.description.items() if text
            } or None
        if self.allowed_functions is not None:
            self.allowed_functions = [
                name.strip() for name in self.allowed_functions if name.strip()
            ] or None
        for field in ("allowed_domains", "blocked_domains"):
            values = getattr(self, field)
            if values is not None:
                normalized = [_normalize_domain(v) for v in values if v.strip()]
                setattr(self, field, list(dict.fromkeys(normalized)) or None)
        if self.allowed_domains and self.blocked_domains:
            raise PydanticCustomError(
                "domains_conflict",
                "Set allowed domains or blocked domains, not both.",
            )
        return self


class ToolAdmin(ToolBase):
    """What the admin panel is allowed to see: whether a credential is set,
    never the credential."""

    has_secret: bool = False
    logo_url: str | None = None


class ToolPublic(SQLModel):
    """
    What a visitor is told about a tool.

    Deliberately not derived from ToolBase: the arena serves this without
    authentication, and inheriting would hand out the server address and its
    credentials the moment either is added to the row.
    """

    key: str
    label: str
    description: str | None = None
    logo_url: str | None = None
    enabled: bool
