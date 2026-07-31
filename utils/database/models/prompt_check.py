"""
The check run on a user prompt before it reaches the arena models.

One call to the Mistral moderation API scores eleven categories between 0 and 1.
Each category carries its own threshold and its own action, so an instance can
block sexual content, warn about personal data and merely log the rest without
that being three separate systems: it is one request and one configuration.

See .scratch/prompt-checks/spec.md for the benchmark behind the seeded values.
"""

import uuid
from typing import Annotated, Literal

from pydantic import field_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime

PromptCheckAction = Literal["off", "log", "warn", "block"]

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

# Seeded off rather than forbidden. On a sante or juridique instance these
# categories describe the product, so acting on them would refuse the very
# prompts the platform exists for. An admin who knows their instance can still
# turn them on, and the page says why they start off.
OFF_BY_DEFAULT = ("health", "law", "financial")

# Ordered weakest to strongest. The prompt takes the strongest action any
# triggered category asks for.
_ACTION_RANK = {"off": 0, "log": 1, "warn": 2, "block": 3}

# Seeded configuration. Everything starts on log: nothing is refused or shown to
# anyone until an admin has watched the verdicts on real traffic.
#
# `sexual` and `selfharm` sit below the rest on purpose. Mistral has no
# minor-specific category and scores an explicit request involving a child at
# 0.41, so a 0.5 threshold misses it.
DEFAULT_CATEGORIES: dict[str, dict] = {
    "sexual": {"threshold": 0.3, "action": "log"},
    "selfharm": {"threshold": 0.3, "action": "log"},
    "hate_and_discrimination": {"threshold": 0.5, "action": "log"},
    "violence_and_threats": {"threshold": 0.5, "action": "log"},
    "dangerous": {"threshold": 0.5, "action": "log"},
    "criminal": {"threshold": 0.5, "action": "log"},
    "jailbreaking": {"threshold": 0.5, "action": "log"},
    "pii": {"threshold": 0.5, "action": "log"},
    "health": {"threshold": 0.5, "action": "off"},
    "law": {"threshold": 0.5, "action": "off"},
    "financial": {"threshold": 0.5, "action": "off"},
}


def validate_categories(value: object) -> dict[str, dict]:
    if not isinstance(value, dict):
        raise ValueError("Categories must be an object")

    result: dict[str, dict] = {}
    for category, config in value.items():
        if category not in MISTRAL_CATEGORIES:
            raise ValueError(f"Unknown category '{category}'")
        if not isinstance(config, dict):
            raise ValueError(f"Category '{category}' must be an object")

        threshold = config.get("threshold")
        if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
            raise ValueError(f"Threshold for '{category}' must be a number")
        if not 0 <= threshold <= 1:
            raise ValueError(f"Threshold for '{category}' must be between 0 and 1")

        action = config.get("action")
        if action not in _ACTION_RANK:
            raise ValueError(f"Unknown action '{action}' for '{category}'")

        result[category] = {"threshold": float(threshold), "action": action}

    missing = set(MISTRAL_CATEGORIES) - set(result)
    if missing:
        raise ValueError(f"Missing categories: {', '.join(sorted(missing))}")
    return result


class PromptCheck(SQLModel, table=True):
    """Singleton row (id=1) holding the prompt check configuration."""

    __tablename__ = "prompt_check"

    id: int = Field(default=1, primary_key=True)
    model: str = Field(default=DEFAULT_MODEL)
    categories: Annotated[dict[str, dict], Field(sa_type=JSONB)] = {}
    updated_at: AutoDatetime
    updated_by: uuid.UUID | None = Field(default=None, foreign_key="auth_user.id")

    def triggered(self, scores: dict[str, float]) -> dict[str, str]:
        """Categories whose score reaches their threshold, mapped to their action.

        Categories set to `off` never trigger, so a prompt that only scores on
        those is indistinguishable from a clean one.
        """
        return {
            category: config["action"]
            for category, config in self.categories.items()
            if config["action"] != "off"
            and scores.get(category, 0.0) >= config["threshold"]
        }

    def action_for(self, scores: dict[str, float]) -> str:
        """The strongest action any triggered category asks for."""
        actions = self.triggered(scores).values()
        return max(actions, key=lambda a: _ACTION_RANK[a], default="off")

    @property
    def is_enabled(self) -> bool:
        """False when every category is off, in which case no call is made."""
        return any(config["action"] != "off" for config in self.categories.values())


class PromptCheckPublic(SQLModel):
    model: str
    categories: dict[str, dict]
    updated_at: str
    updated_by: uuid.UUID | None = None


class PromptCheckStatus(PromptCheckPublic):
    """The configuration plus how the check is faring. It fails open, so one
    that has stopped working looks exactly like one that finds nothing."""

    consecutive_failures: int = 0
    healthy: bool = True
    # Warnings put in front of someone. The turns only record the people who
    # sent anyway, so this is what that number is measured against.
    warnings_shown: int = 0


class PromptCheckPatch(SQLModel):
    model: str | None = None
    categories: dict[str, dict] | None = None

    @field_validator("categories", mode="before")
    @classmethod
    def check_categories(cls, value: object) -> dict[str, dict] | None:
        return None if value is None else validate_categories(value)
