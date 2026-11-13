import uuid

from pydantic import BaseModel

from utils.database.models import ModeIcon, ModeViability, SelectionModeRules
from utils.i18n import TranslatableRaw


class SelectionModeOrder(BaseModel):
    """The whole menu order, written in one request."""

    ids: list[uuid.UUID]


class PreviewLLM(BaseModel):
    id: uuid.UUID
    name: str
    lab: str
    # False for a system that brings its own tools: it never gets the arena's.
    arena_tools: bool


class SelectionModePreview(BaseModel):
    viability: ModeViability
    # Without a pool B, both lists are pool A.
    pool_a: list[PreviewLLM]
    pool_b: list[PreviewLLM]
    # A few pairs drawn the way the arena would, without visitor picks. Pool
    # A's model comes first; the arena itself shows them in random order.
    sample_draws: list[tuple[PreviewLLM, PreviewLLM]]


class SelectionModeDraft(SelectionModeRules):
    """A mode not saved yet, as a template fills the create form."""

    key: str = ""
    label: TranslatableRaw[str] = {}
    short_label: TranslatableRaw[str] = {}
    description: TranslatableRaw[str] = {}
    icon: ModeIcon = "i-ri-dice-line"


class SelectionModeTemplate(BaseModel):
    # Also the key of its title and description in the frontend messages.
    id: str
    mode: SelectionModeDraft
