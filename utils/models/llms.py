from typing import Annotated, Any, Literal

from pydantic import (
    Field,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticCustomError

from backend.llms.models import (
    FRIENDLY_SIZE,
    CountryPortal,
    Distribution,
    Endpoint,
    FriendlySize,
    LLMDataBase,
    LLMDataEnhanced,
)
from backend.llms.utils import convert_range_to_value, get_llm_impact
from utils.utils import MarkdownSerializer

descs = {
    "new": "Whether this is a newly added LLM",
    "status": "This LLM data status",
    "id": "Unique LLM identifier (you can choose it or use HF one)",
    "simple_name": "Human-readable LLM name",
    "license": "License identifier (maps to `licenses.json` ids)",
    "fully_open_source": "Whether LLM weights are fully open/public",
    "release_date": "LLM release date in MM/YYYY format",
    "arch": "LLM architecture (maps to `archs.json` ids). Use `maybe-*` if information is not confirmed",
    "params": "Total parameters in billions",
    "active_params": "Active parameters in billions (only for MoE LLMs)",
    "reasoning": "Extended thinking capability",
    "quantization": "Quantization scheme applied (q4, q8, or None for full precision)",
    "url": "LLM homepage or documentation URL",
    "endpoint": "API access configuration (None for unavailable LLMs)",
    "pricey": "Whether LLM has high API costs (triggers stricter rate limits)",
    "specific_portals": "Custom allow list of country portals on which the LLM is available",
    "desc": "Detailed LLM description",
    "size_desc": "Detailed description of LLM size",
    "fyi": "Additional notes for users",
}


# Raw LLM definitions from 'utils/models/models.json'
class LLMDataRawBase(LLMDataBase):
    """
    Individual LLM raw model definition (before enrichment).

    Raw LLM data loaded from `utils/models/models.json`.
    Contains basic LLM information (name, params, licensing).
    Gets enriched with license data, architecture info, and rankings to become `LLMDataRaw` class.
    """

    new: Annotated[bool, Field(description=descs["new"])] = False
    status: Annotated[
        Literal["archived", "missing_data", "disabled", "enabled"],
        Field(description=descs["status"]),
    ] = "enabled"
    id: Annotated[str, Field(description=descs["id"])]
    simple_name: Annotated[str, Field(description=descs["simple_name"])]
    license: Annotated[str, Field(description=descs["license"])]
    fully_open_source: Annotated[
        bool, Field(description=descs["fully_open_source"])
    ] = False
    release_date: Annotated[
        str, Field(pattern=r"^[0-9]{02}/[0-9]{4}$", description=descs["release_date"])
    ]
    arch: Annotated[str, Field(description=descs["arch"])]
    params: Annotated[int | float, Field(description=descs["params"])]
    active_params: Annotated[
        int | float | None, Field(description=descs["active_params"])
    ] = None
    reasoning: Annotated[
        bool | Literal["hybrid"], Field(description=descs["reasoning"])
    ] = False
    quantization: Annotated[
        Literal["q4", "q8"] | None, Field(description=descs["quantization"])
    ] = None
    url: Annotated[str | None, Field(description=descs["url"])] = (
        None  # FIXME required?
    )
    endpoint: Annotated[Endpoint | None, Field(description=descs["endpoint"])] = None
    pricey: Annotated[bool, Field(description=descs["pricey"])] = False
    specific_portals: Annotated[
        list[CountryPortal] | None, Field(description=descs["specific_portals"])
    ] = None

    # Raw specific fields
    desc: Annotated[str, MarkdownSerializer, Field(description=descs["desc"])]
    size_desc: Annotated[str, MarkdownSerializer, Field(description=descs["size_desc"])]
    fyi: Annotated[str, MarkdownSerializer, Field(description=descs["fyi"])]

    @field_validator("arch", mode="after")
    @classmethod
    def check_arch_exists(cls, value: str, info: ValidationInfo) -> str:
        assert info.context is not None
        assert info.context["archs"] is not None

        if value.replace("maybe-", "") not in info.context["archs"]:
            raise PydanticCustomError(
                "missing_arch",
                f"Missing arch '{value.replace("maybe-", "")}' infos in 'archs.json'.",
            )

        if info.data.get("license") != "proprietary" and "maybe" in value:
            raise PydanticCustomError(
                "wrong_arch",
                f"Arch should not be 'maybe' since license is not 'proprietary'.",
            )

        return value

    @field_validator("active_params", mode="before")
    @classmethod
    def check_active_params_is_defined_if_moe(
        cls, value: int | float | None, info: ValidationInfo
    ) -> int | float | None:
        if "arch" in info.data and "moe" in info.data.get("arch", "") and value is None:
            raise PydanticCustomError(
                "missing_active_params",
                f"Model's arch is '{info.data['arch']}' and requires 'active_params' to be defined.",
            )

        return value

    @model_validator(mode="after")
    def check_endpoint(self):
        if self.status == "enabled" and not self.endpoint:
            raise PydanticCustomError(
                "endpoint", "Model is enabled but no endpoint has been found."
            )
        return self


# Enriched LLM definition generated from LLMDataRawBase + licenses + rankings + preferences
class LLMDataRaw(LLMDataEnhanced, LLMDataRawBase):  # type: ignore
    """
    Complete LLM raw definition with enriched metadata.

    Inherits from `LLMDataEnhanced` and `LLMDataRawBase` and adds:
    - License data (distribution, reuse rights)
    - Organisation/vendor information
    - Ranking data (Elo, confidence intervals)
    - User preference statistics
    - Computed fields (friendly size, RAM requirements, energy impact)

    Generated by `build_models.py` from `utils/models/models.json` and saved as
    `utils/models/generated-models.json`.

    !Warning: Make sure to reflect changes of computed props to `LLMData`.

    Attributes:
        distribution: How the LLM is distributed (from license)
        reuse: Whether the LLM can be reused/redistributed (from license)
        commercial_use: Whether commercial use is permitted (from license)
        organisation: Organisation's name (from organisation)
        icon_path: Icon (from organisation)
        data: Ranking data
        prefs: Preference data

    Computed Properties:
        friendly_size: Human-readable category (XS, S, M, L, XL) based on params
        required_ram: Estimated RAM needed to run the LLM (depends on quantization)
        wh_per_million_token: Energy consumption per million tokens
    """

    status: Literal["archived", "enabled", "disabled"] = "enabled"

    @model_validator(mode="before")
    @classmethod
    def insert_defaults(cls, data: Any) -> Any:
        """
        Insert default values, that way we do not need to repeat types and
        make sure we are based on `LLMDataEnhanced` types.
        """
        DEFAULTS = {
            "commercial_use": None,
            "data": None,
            "prefs": None,
        }
        for key, value in DEFAULTS.items():
            if not key in data:
                data[key] = value

        return data

    @field_validator("distribution", mode="before")
    @classmethod
    def check_distribution(
        cls, value: Distribution, info: ValidationInfo
    ) -> Distribution:
        if info.data["fully_open_source"]:
            value = "fully-open-source"

        return value

    @computed_field  # type: ignore[prop-decorator]
    @property
    def friendly_size(self) -> FriendlySize:
        intervals = [(0, 15), (15, 60), (60, 100), (100, 400), (400, float("inf"))]

        for i, (lower, upper) in enumerate(intervals):
            if lower <= self.params < upper:
                return FRIENDLY_SIZE[i]

        raise Exception("Error: Could not guess friendly_size")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def required_ram(self) -> int | float:
        if self.quantization == "q8":
            return self.params * 2

        # We suppose from q4 to fp16
        return self.params

    @computed_field  # type: ignore[prop-decorator]
    @property
    def wh_per_million_token(self) -> int | float:
        impact = get_llm_impact(self, 1_000_000, None)
        energy_kwh = convert_range_to_value(impact.energy.value)

        return energy_kwh * 1000
