import uuid

from pydantic import BaseModel

from utils.database.models import ModeViability, SelectionModeRules


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

