import uuid
from datetime import date, datetime
from typing import Annotated, Any, Literal, get_args

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, StringConstraints, model_validator
from pydantic_core import PydanticCustomError
from sqlalchemy import Index, Integer, TypeDecorator, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlmodel import Field, SQLModel, String

from utils.i18n import SupportedLocale, TranslatableRaw

from .llms.constants import EnergyClass, LLMArchKind, LLMInput, SizeClass
from .llms.llm import Tags
from .suggestion import CategoryIcon
from .utils import BaseDBModel, as_naive_utc

# How the two drawn models must relate. A visitor's own picks are exempt:
# they chose.
Pairing = Literal[
    "any", "different_lab", "same_lab", "different_size_class", "same_size_class"
]
PAIRINGS: tuple[Pairing, ...] = get_args(Pairing)
# How draws are weighted inside a pool.
Sampling = Literal["uniform", "fewer_votes", "newest"]
SAMPLINGS: tuple[Sampling, ...] = get_args(Sampling)
# Who decides which tools the models get. Enforced on the server: a mode set to
# "none" gets no tools whatever the client sends.
ToolsPolicy = Literal["visitor", "none", "forced"]
TOOLS_POLICIES: tuple[ToolsPolicy, ...] = get_args(ToolsPolicy)
VisitorPicks = Literal[0, 1, 2]
TagsMatch = Literal["any", "all"]

# Why a mode cannot run, or may not run as the admin expects. Keys the admin
# panel translates.
ViabilityWarning = Literal[
    "pool_a_empty",
    "pool_b_empty",
    "no_valid_pair",
    "single_pair",
    "unknown_llm_ids",
    "unknown_tool_keys",
    "tool_not_offered",
]

# The icons an admin may give a mode, generated into the frontend constants
# and safelisted there.
ModeIcon = Literal[
    "i-ri-dice-line",
    "i-ri-scales-3-line",
    "i-ri-open-source-line",
    "i-ri-map-pin-line",
    "i-ri-ruler-line",
    "i-ri-leaf-line",
    "i-ri-trophy-line",
    "i-ri-sparkling-line",
    "i-ri-group-line",
    "i-ri-search-line",
    "i-ri-global-line",
    "i-ri-government-line",
    "i-ri-heart-pulse-line",
    "i-ri-stethoscope-line",
    "i-ri-graduation-cap-line",
    "i-ri-shield-check-line",
    "i-ri-flashlight-line",
]
MODE_ICONS: tuple[ModeIcon, ...] = get_args(ModeIcon)

# A cohort as the arena reads it from `?c=`: comma-separated, so a name with a
# comma, a space or a capital could never match a visitor.
Cohort = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9-]{1,50}$"),
]

# Stored on every comparison and published with the dataset, so it never
# changes once created.
ModeKey = Annotated[
    str,
    StringConstraints(strip_whitespace=True, pattern=r"^[a-z0-9][a-z0-9-]{0,49}$"),
]

FILTER_FIELDS = {
    "llm_ids": {
        "title": "Only these models",
        "description": "Leave empty to keep every model that meets the other criteria.",
    },
    "exclude_llm_ids": {"title": "Except these models"},
    "lab_ids": {"title": "Only these labs"},
    "exclude_lab_ids": {"title": "Except these labs"},
    "tags": {
        "title": "With these tags",
        "description": "Tags set on the models in the LLM form.",
    },
    "exclude_tags": {"title": "Without these tags"},
    "tags_match": {
        "title": "Models must carry",
        "description": "any: at least one of the tags; all: every tag.",
    },
    "license_ids": {"title": "Only these licences"},
    "public_weights": {
        "title": "Weights",
        "description": "Yes: open weights only. No: proprietary only.",
    },
    "eu_hostable": {"title": "Can be hosted in the European Union"},
    "archs": {"title": "Architectures"},
    "size_classes": {
        "title": "Size classes",
        "description": "In billions of parameters.",
    },
    "params_min": {"title": "Minimum parameters", "description": "In billions."},
    "params_max": {"title": "Maximum parameters", "description": "In billions."},
    "energy_classes": {
        "title": "Energy classes",
        "description": "From A, the lowest estimated consumption, to F, the highest.",
    },
    "inputs": {
        "title": "Accepted inputs",
        "description": "The model accepts every one of these.",
    },
    "released_after": {"title": "Released on or after"},
    "released_before": {"title": "Released on or before"},
    "released_within_days": {
        "title": "Released in the last (days)",
        "description": "For example 90 for the last three months.",
    },
    "price_out_max": {
        "title": "Maximum output price",
        "description": "In US dollars per million output tokens.",
    },
    "rate_limited": {
        "title": "Rate limited models",
        "description": "Rate limited models are the expensive ones, with a usage cap per visitor.",
    },
    "arena_tools": {
        "title": "Arena's tools",
        "description": "Set per model in the LLM form. A system with its own retrieval or tools behind its endpoint never gets the arena's.",
    },
    "top_ranked": {
        "title": "Among the best ranked",
        "description": "Only the N first models of the ranking. Models not ranked yet never match.",
    },
}


class ModelFilter(SQLModel):
    """
    Which models a side of a mode draws from. Every field is optional and an
    empty filter matches every enabled model. A model matches when it passes
    every field that is set.
    """

    llm_ids: Annotated[list[uuid.UUID], Field(**FILTER_FIELDS["llm_ids"])] = []
    exclude_llm_ids: Annotated[
        list[uuid.UUID], Field(**FILTER_FIELDS["exclude_llm_ids"])
    ] = []
    lab_ids: Annotated[list[uuid.UUID], Field(**FILTER_FIELDS["lab_ids"])] = []
    exclude_lab_ids: Annotated[
        list[uuid.UUID], Field(**FILTER_FIELDS["exclude_lab_ids"])
    ] = []
    tags: Annotated[Tags, Field(**FILTER_FIELDS["tags"])] = []
    exclude_tags: Annotated[Tags, Field(**FILTER_FIELDS["exclude_tags"])] = []
    tags_match: Annotated[TagsMatch, Field(**FILTER_FIELDS["tags_match"])] = "any"
    license_ids: Annotated[list[uuid.UUID], Field(**FILTER_FIELDS["license_ids"])] = []
    public_weights: Annotated[bool | None, Field(**FILTER_FIELDS["public_weights"])] = (
        None
    )
    eu_hostable: Annotated[bool | None, Field(**FILTER_FIELDS["eu_hostable"])] = None
    archs: Annotated[list[LLMArchKind], Field(**FILTER_FIELDS["archs"])] = []
    size_classes: Annotated[list[SizeClass], Field(**FILTER_FIELDS["size_classes"])] = (
        []
    )
    params_min: Annotated[float | None, Field(ge=0, **FILTER_FIELDS["params_min"])] = (
        None
    )
    params_max: Annotated[float | None, Field(ge=0, **FILTER_FIELDS["params_max"])] = (
        None
    )
    energy_classes: Annotated[
        list[EnergyClass], Field(**FILTER_FIELDS["energy_classes"])
    ] = []
    inputs: Annotated[list[LLMInput], Field(**FILTER_FIELDS["inputs"])] = []
    released_after: Annotated[date | None, Field(**FILTER_FIELDS["released_after"])] = (
        None
    )
    released_before: Annotated[
        date | None, Field(**FILTER_FIELDS["released_before"])
    ] = None
    released_within_days: Annotated[
        int | None, Field(ge=1, **FILTER_FIELDS["released_within_days"])
    ] = None
    price_out_max: Annotated[
        float | None, Field(ge=0, **FILTER_FIELDS["price_out_max"])
    ] = None
    rate_limited: Annotated[bool | None, Field(**FILTER_FIELDS["rate_limited"])] = None
    arena_tools: Annotated[bool | None, Field(**FILTER_FIELDS["arena_tools"])] = None
    top_ranked: Annotated[int | None, Field(ge=1, **FILTER_FIELDS["top_ranked"])] = None

    @model_validator(mode="after")
    def check_ranges(self):
        if (
            self.params_min is not None
            and self.params_max is not None
            and self.params_min > self.params_max
        ):
            raise PydanticCustomError(
                "invalid_params_range",
                "The minimum parameters are above the maximum.",
            )
        if (
            self.released_after is not None
            and self.released_before is not None
            and self.released_after > self.released_before
        ):
            raise PydanticCustomError(
                "invalid_release_range",
                "The release window ends before it starts.",
            )
        return self


class FilterJSONB(TypeDecorator):
    """
    JSONB that takes a ModelFilter. A table row hands its values to the driver
    as they are, and the driver cannot serialise a pydantic model. Read back,
    the value is a plain dict until a non-table model validates the row.
    """

    impl = JSONB
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        return None if value is None else jsonable_encoder(value)


FIELDS = {
    "key": {
        "description": "Lowercase letters, digits and dashes. Stored on every comparison and published with the dataset: it cannot be changed once saved.",
    },
    "label": {
        "title": "Name",
        "description": "Required in the instance's main language. Shown in the arena's mode menu.",
    },
    "short_label": {
        "title": "Short name",
        "description": "Shown on the closed menu button. Leave empty to reuse the name.",
    },
    "description": {
        "description": "One line under the name, to say what the visitor will get.",
    },
    "icon": {"description": "One of the icons the admin picker offers."},
    "enabled": {
        "title": "Offered in the arena",
        "description": "The arena needs at least one mode switched on.",
    },
    "position": {"description": "Order in the mode menu, smallest first."},
    "is_default": {
        "title": "Default mode",
        "description": "Preselected when a visitor arrives. Only one mode is the default: this one replaces the current one.",
    },
    # The four choices below describe each of their values in the admin form.
    "visitor_picks": {"title": "Models the visitor picks"},
    "pool_a": {
        "title": "Pool A",
        "description": "Models side A is drawn from.",
    },
    "pool_b": {
        "title": "Pool B",
        "description": "Models side B is drawn from. Leave empty to draw both sides from pool A.",
    },
    "pairing": {"title": "The two models"},
    "sampling": {"title": "Which models come up most"},
    "tools_policy": {"title": "Who decides"},
    "tool_keys": {
        "title": "Tools of the mode",
        "description": "With 'forced', the tools always on. With 'visitor', the only tools offered; leave empty to offer every tool.",
    },
    "cohorts": {
        "description": "Offered only to visitors who came with one of these cohorts in the address, as in ?c=pix.",
    },
    "locales": {
        "title": "Languages",
        "description": "Offered only when the arena is shown in one of these languages.",
    },
    "starts_at": {
        "title": "Starts at",
        "description": "Offered from this time on (UTC).",
    },
    "ends_at": {
        "title": "Ends at",
        "description": "Offered until this time (UTC).",
    },
}


class SelectionModeBase(BaseDBModel):
    key: Annotated[
        ModeKey, Field(sa_type=String, unique=True, index=True, **FIELDS["key"])
    ]
    label: Annotated[TranslatableRaw[str], Field(sa_type=JSONB, **FIELDS["label"])]
    short_label: Annotated[
        TranslatableRaw[str], Field(sa_type=JSONB, **FIELDS["short_label"])
    ] = {}
    description: Annotated[
        TranslatableRaw[str], Field(sa_type=JSONB, **FIELDS["description"])
    ] = {}
    icon: Annotated[CategoryIcon, Field(sa_type=String, **FIELDS["icon"])]
    enabled: Annotated[bool, Field(**FIELDS["enabled"])] = True
    position: Annotated[int, Field(ge=0, **FIELDS["position"])] = 0
    is_default: Annotated[bool, Field(**FIELDS["is_default"])] = False
    visitor_picks: Annotated[
        VisitorPicks, Field(sa_type=Integer, **FIELDS["visitor_picks"])
    ] = 0
    pool_a: Annotated[
        ModelFilter,
        Field(sa_type=FilterJSONB, default_factory=ModelFilter, **FIELDS["pool_a"]),
    ]
    pool_b: Annotated[
        ModelFilter | None, Field(sa_type=FilterJSONB, **FIELDS["pool_b"])
    ] = None
    pairing: Annotated[Pairing, Field(sa_type=String, **FIELDS["pairing"])] = "any"
    sampling: Annotated[Sampling, Field(sa_type=String, **FIELDS["sampling"])] = (
        "uniform"
    )
    tools_policy: Annotated[
        ToolsPolicy, Field(sa_type=String, **FIELDS["tools_policy"])
    ] = "visitor"
    tool_keys: Annotated[list[str], Field(sa_type=JSONB, **FIELDS["tool_keys"])] = []
    cohorts: Annotated[list[Cohort], Field(sa_type=JSONB, **FIELDS["cohorts"])] = []
    locales: Annotated[
        list[SupportedLocale], Field(sa_type=JSONB, **FIELDS["locales"])
    ] = []
    starts_at: Annotated[
        datetime | None, Field(sa_type=TIMESTAMP, **FIELDS["starts_at"])
    ] = None
    ends_at: Annotated[
        datetime | None, Field(sa_type=TIMESTAMP, **FIELDS["ends_at"])
    ] = None


class SelectionMode(SelectionModeBase, table=True):
    """How the arena picks the two models of a comparison, designed by an admin."""

    __tablename__ = "selection_mode"
    # One default at most, even when two admins save at once.
    __table_args__ = (
        Index(
            "ix_selection_mode_one_default",
            "is_default",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )


def _strip_list(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def _drop_empty(values: TranslatableRaw[str]) -> TranslatableRaw[str]:
    return {locale: text.strip() for locale, text in values.items() if text.strip()}


class SelectionModeUpsert(SelectionModeBase):
    # Narrower than the row, which keeps reading a mode saved before an icon
    # left the list.
    icon: Annotated[ModeIcon, Field(**FIELDS["icon"])]

    @model_validator(mode="after")
    def check_mode(self):
        """
        Checked on the model rather than per field: several rules read two
        fields at once, and fields left at their default skip field validators.
        """
        self.label = _drop_empty(self.label)
        if not self.label:
            raise PydanticCustomError("label_required", "A mode needs a label.")
        self.short_label = _drop_empty(self.short_label)
        self.description = _drop_empty(self.description)
        self.tool_keys = _strip_list(self.tool_keys)
        self.cohorts = _strip_list(self.cohorts)
        self.locales = list(dict.fromkeys(self.locales))
        if self.tools_policy == "forced" and not self.tool_keys:
            raise PydanticCustomError(
                "forced_tools_required",
                "A mode that forces tools needs at least one tool.",
            )
        # Compared with the database's naive UTC clock.
        if self.starts_at is not None:
            self.starts_at = as_naive_utc(self.starts_at)
        if self.ends_at is not None:
            self.ends_at = as_naive_utc(self.ends_at)
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise PydanticCustomError(
                "invalid_window", "The mode ends before it starts."
            )
        return self


class SelectionModeRules(BaseModel):
    """
    What the draw reads from a mode. A mode row has these fields too; this is
    for rules that are not a row, like a mode being edited in the admin.
    """

    visitor_picks: VisitorPicks = 0
    pool_a: ModelFilter = ModelFilter()
    pool_b: ModelFilter | None = None
    pairing: Pairing = "any"
    sampling: Sampling = "uniform"
    tools_policy: ToolsPolicy = "visitor"
    tool_keys: list[str] = []


class ModeViability(BaseModel):
    """Whether a mode can draw a pair now, and what an admin should know."""

    viable: bool
    pool_a_size: int
    pool_b_size: int
    # Unordered pairs of two different models the pairing rule allows.
    pairs: int
    warnings: list[ViabilityWarning] = []


class SelectionModeAdmin(SelectionModeBase):
    viability: ModeViability


class SelectionModePublic(SQLModel):
    """
    What a visitor is told about a mode on offer. Deliberately not derived from
    SelectionModeBase: the arena serves it without authentication, and the
    pools of a blind mode would tell a visitor what they are voting on.
    """

    key: str
    # Already picked for the visitor's locale.
    label: str
    short_label: str
    description: str | None = None
    icon: str
    is_default: bool
    visitor_picks: VisitorPicks
    tools_policy: ToolsPolicy
    # The tools the visitor may get in this mode, among those on offer: the
    # forced ones, or the ones they may choose from.
    tool_keys: list[str]
    # The models in the mode's pools, locked ones included (the arena greys
    # them). None when the mode is a blind draw.
    llm_ids: list[uuid.UUID] | None = None
    # Each pool on its own, only when the visitor may pick two models in a
    # mode with two pools: the picker then greys what cannot face the first
    # pick. None otherwise.
    llm_ids_a: list[uuid.UUID] | None = None
    llm_ids_b: list[uuid.UUID] | None = None
