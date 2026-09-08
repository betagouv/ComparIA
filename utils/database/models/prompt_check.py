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

from pydantic import computed_field, field_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from .utils import AutoDatetime, ModelId

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

# Seeded configuration. A fresh install has to be safe before anyone has looked
# at it, so the categories that describe abuse rather than a topic act straight
# away: `jailbreaking` refuses the prompt, `sexual` and `selfharm` ask the user
# to confirm. Loosening any of them is then a deliberate admin decision, not the
# result of nobody having touched the page yet. The rest stay on log, where they
# cost nothing and build the picture an admin needs before acting on them.
#
# `sexual` and `selfharm` sit below the rest on purpose. Mistral has no
# minor-specific category and scores an explicit request involving a child at
# 0.41, so a 0.5 threshold misses it.
DEFAULT_CATEGORIES: dict[str, dict] = {
    "sexual": {"threshold": 0.3, "action": "warn"},
    "selfharm": {"threshold": 0.3, "action": "warn"},
    "hate_and_discrimination": {"threshold": 0.5, "action": "log"},
    "violence_and_threats": {"threshold": 0.5, "action": "log"},
    "dangerous": {"threshold": 0.5, "action": "log"},
    "criminal": {"threshold": 0.5, "action": "log"},
    "jailbreaking": {"threshold": 0.5, "action": "block"},
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
    enabled: bool = Field(default=True)
    model: str = Field(default=DEFAULT_MODEL)
    # Overrides MISTRAL_API_KEY when set, so an instance can be configured
    # without a redeploy. Never leaves the backend: PromptCheckPublic reports
    # whether one is set, not what it is.
    api_key: str | None = Field(default=None)
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
    def should_run(self) -> bool:
        """Whether a message is worth a call.

        False when the check is switched off, and also when every category is
        `off`, since then no score could change anything.
        """
        return self.enabled and any(
            config["action"] != "off" for config in self.categories.values()
        )


class PromptCheckPublic(SQLModel):
    enabled: bool
    model: str
    # Whether a key is stored, never the key itself.
    has_api_key: bool
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
    enabled: bool | None = None
    model: str | None = None
    # Write-only. An empty string clears the stored key and falls back to the
    # environment variable.
    api_key: str | None = None
    categories: dict[str, dict] | None = None

    @field_validator("categories", mode="before")
    @classmethod
    def check_categories(cls, value: object) -> dict[str, dict] | None:
        return None if value is None else validate_categories(value)


class PromptCheckResult(SQLModel, table=True):
    """
    Prompt check result based on prompt checker.
    Linked to a Turn if not blocked.
    """

    __tablename__ = "prompt_check_result"

    id: ModelId
    created_at: AutoDatetime
    turn_id: uuid.UUID | None = Field(default=None, foreign_key="turn.id", unique=True)

    decision: str  # pass | logged | warned | blocked | error
    model: str
    latency_ms: int
    scores: Annotated[dict[str, float], Field(sa_type=JSONB)] = {}
    triggered: Annotated[dict[str, str], Field(sa_type=JSONB)] = {}
    message: str | None = None
    user_proceeded: bool = False

    @computed_field  # type: ignore[prop-decorator]
    @property
    def block_message(self) -> str | None:
        return self.message if self.decision == "blocked" else None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pending_warning(self) -> bool:
        """A warning the user has not answered yet, so one to show."""
        return self.decision == "warned" and not self.user_proceeded
