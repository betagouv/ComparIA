"""
Admin-configurable checks run on a user prompt before it reaches the arena.

Two rows, seeded by the migration: `content_safety` and `pii`. Both are served
by one call to the Mistral moderation API, which scores eleven categories
between 0 and 1, so the runner calls Mistral once and derives both verdicts.

See .scratch/prompt-checks/spec.md for the benchmark behind the seeded
thresholds.
"""

import uuid
from typing import Annotated, Literal

from pydantic import field_validator
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime

PromptCheckKind = Literal["content_safety", "pii"]
PromptCheckMode = Literal["off", "log", "warn", "block"]

DEFAULT_MODEL = "mistral-moderation-latest"

# Categories returned by POST https://api.mistral.ai/v1/moderations. Kept here
# rather than fetched: Mistral deprecates model versions (2411 -> 2603), and a
# version that changes the category set needs a code change anyway.
MISTRAL_CATEGORIES = (
    "sexual",
    "hate_and_discrimination",
    "violence_and_threats",
    "dangerous",
    "criminal",
    "selfharm",
    "health",
    "financial",
    "law",
    "pii",
    "jailbreaking",
)

# In a sante or juridique arena these categories describe the product, so they
# must never block. A threshold on any of them is rejected rather than ignored,
# so an admin cannot believe they have set one.
NEVER_BLOCK = ("health", "law", "financial")

# Seeded thresholds. `sexual` and `selfharm` sit below the rest on purpose:
# Mistral has no minor-specific category and scores an explicit request
# involving a child at 0.41, so 0.5 misses it.
DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "content_safety": {
        "sexual": 0.3,
        "selfharm": 0.3,
        "hate_and_discrimination": 0.5,
        "violence_and_threats": 0.5,
        "dangerous": 0.5,
        "criminal": 0.5,
        "jailbreaking": 0.5,
    },
    "pii": {"pii": 0.5},
}


def validate_thresholds(value: object) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError("Thresholds must be an object")
    result: dict[str, float] = {}
    for category, threshold in value.items():
        if category not in MISTRAL_CATEGORIES:
            raise ValueError(f"Unknown category '{category}'")
        if category in NEVER_BLOCK:
            raise ValueError(
                f"Category '{category}' can never block: it is the product in a "
                "sante or juridique arena"
            )
        if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
            raise ValueError(f"Threshold for '{category}' must be a number")
        if not 0 <= threshold <= 1:
            raise ValueError(f"Threshold for '{category}' must be between 0 and 1")
        result[category] = float(threshold)
    return result


class PromptCheck(SQLModel, table=True):
    """One configured check. Exactly two rows exist, seeded by the migration."""

    __tablename__ = "prompt_check"

    id: int | None = Field(default=None, primary_key=True)
    kind: str = Field(sa_type=String, unique=True, index=True)
    mode: str = Field(sa_type=String, default="log")
    thresholds: Annotated[dict[str, float], Field(sa_type=JSONB)] = {}
    model: str = Field(default=DEFAULT_MODEL)
    updated_at: AutoDatetime
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")

    def blocking_categories(self, scores: dict[str, float]) -> list[str]:
        """Categories whose score reaches this check's threshold."""
        return sorted(
            category
            for category, threshold in self.thresholds.items()
            if scores.get(category, 0.0) >= threshold
        )


class PromptCheckPublic(SQLModel):
    kind: PromptCheckKind
    mode: PromptCheckMode
    thresholds: dict[str, float]
    model: str
    updated_at: str
    updated_by: uuid.UUID | None = None


class PromptCheckStatus(PromptCheckPublic):
    """A check plus how it is faring. Both checks fail open, so a check that has
    stopped working looks exactly like a check that passes everything."""

    consecutive_failures: int = 0
    healthy: bool = True
    # Warnings put in front of a user since the check went to 'warn'. The turns
    # only record the people who sent anyway, so this is what that number is
    # measured against.
    warnings_shown: int = 0


class PromptCheckPatch(SQLModel):
    mode: PromptCheckMode | None = None
    thresholds: dict[str, float] | None = None
    model: str | None = None

    @field_validator("thresholds", mode="before")
    @classmethod
    def check_thresholds(cls, value: object) -> dict[str, float] | None:
        return None if value is None else validate_thresholds(value)
