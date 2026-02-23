"""
Environmental impact calculations.

This module computes the ecological impact of LLM inference using the ecologits library,
converting technical metrics (energy, CO2) into user-friendly scaled equivalences
(e.g., "if 1 billion people used this daily for a year").

Functions:
- convert_range_to_value: Normalize impact ranges to single values
- get_total_params: Get the total number of parameters for a LLM
- get_active_params: Get the number of active parameters for a LLM
- get_llm_impact: Calculate environmental impact for a model
- get_llm_consumption: Calculates environmental impact
"""

from enum import Enum
from typing import TYPE_CHECKING, TypedDict, Union

from ecologits.impacts import Impacts
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes
from ecologits.utils.range_value import RangeValue, ValueOrRange

from backend.config import CountryPortal

if TYPE_CHECKING:
    from backend.llms.models import LLMData
    from utils.models.llms import LLMDataRaw


# Equivalence types for scaled impact comparisons
class EquivalenceType(Enum):
    PACKAGE_DELIVERY = "package_delivery"
    PARIS_NYC_FLIGHTS = "paris_nyc_flights"
    PARIS_BERLIN_TGV = "paris_berlin_tgv"
    BAGUETTE_PRODUCTION = "baguette_production"
    PIZZA_PRODUCTION = "pizza_production"
    MANGO_IMPORT = "mango_import"
    POOL_FILING = "pool_filing"
    ARTIC_SEA_ICE_MELT = "arctic_sea_ice_melt"
    ONE_YEAR_TREE_ABSORTION = "one_year_tree_absortion"


# Reference data for scaled equivalences
# Population using generative AI
SCALE_FACTORS: dict[CountryPortal, float] = {
    # 48% of ppl aged 12 or more in 2026 https://www.credoc.fr/publications/barometre-du-numerique-2026-rapport
    # population count of 12 or more in 2024 https://www.insee.fr/fr/statistiques/7746192?sommaire=7746197
    "fr": 59_315_947 * 0.48,
    # 48.4% of ppl aged 16–74 in 2025 https://ec.europa.eu/eurostat/fr/web/products-eurostat-news/w/ddn-20251216-3
    # population count of 16-74 https://en.wikipedia.org/wiki/Demographics_of_Denmark
    "da": 4_350_000 * 0.484,
}

CO2_KG_EQUIVALENCE: dict[EquivalenceType, float] = {
    EquivalenceType.PACKAGE_DELIVERY: 0.576,
    EquivalenceType.PARIS_NYC_FLIGHTS: 0.177894 * 5837,
    EquivalenceType.PARIS_BERLIN_TGV: 7.26,
    EquivalenceType.BAGUETTE_PRODUCTION: 0.7767000000000001,
    EquivalenceType.PIZZA_PRODUCTION: 3.5994,
    EquivalenceType.MANGO_IMPORT: 11.655508000000001,
    EquivalenceType.POOL_FILING: 7.54,
    EquivalenceType.ARTIC_SEA_ICE_MELT: 1 / 0.003,
    EquivalenceType.ONE_YEAR_TREE_ABSORTION: 22,
}


def convert_range_to_value(value_or_range: ValueOrRange) -> int | float:
    """
    Convert impact range to a single representative value.

    Some impacts are returned as ranges [min, max]; this takes the average.
    Single values are returned as-is.

    Args:
        value_or_range: Either a range object with min/max attributes or a scalar value

    Returns:
        float: Average of range, or the value itself if scalar
    """

    if isinstance(value_or_range, RangeValue):
        return (value_or_range.min + value_or_range.max) / 2
    else:
        return value_or_range


def get_total_params(model: Union["LLMDataRaw", "LLMData"]) -> int:
    """
    Get the total number of parameters for a model.

    Accounts for q8 quantization which reduces effective parameters by half.

    Args:
        model: LLMDataRaw or LLMData with 'params' and optional 'quantization'

    Returns:
        int: Total parameters, or None if params not available
    """
    # Q8 quantization reduces parameter count (2x compression)
    if model.quantization == "q8":
        return int(model.params) // 2
    else:
        return int(model.params)


def get_active_params(model: Union["LLMDataRaw", "LLMData"]) -> int:
    """
    Get the number of active parameters for a model.

    For Mixture of Experts (MoE) models, this is different from total parameters.
    Active params represent how many parameters are used for each token.

    Args:
        model: LLMDataRaw or LLMData

    Returns:
        int: Active parameters, or total params if not available
    """
    if model.active_params:
        # Account for Q8 quantization if present
        if model.quantization == "q8":
            return int(model.active_params) // 2
        else:
            return int(model.active_params)
    else:
        # Fallback to total params if active_params is not available (non-MoE models)
        return get_total_params(model)


def get_llm_impact(
    model: Union["LLMDataRaw", "LLMData"],
    token_count: int,
    request_latency: float | None,
) -> Impacts:
    """
    Calculate environmental impact (energy, CO2) for LLM inference.

    Uses the ecologits library to compute impact based on model parameters and token usage.
    Currently not all models are in ecologits' database, so this uses estimated parameters instead.

    Args:
        model: LLMDataRaw or LLMData with 'params' and optional 'active_params' (MoE)
        token_count: Total output tokens generated
        request_latency: Time taken for inference (optional, for more accurate calculations)

    Returns:
        Impact object with .energy.value and .gwp.value (CO2) attributes

    Impact Metrics:
        - energy: Electricity consumption in kWh
        - gwp: Global Warming Potential (CO2 equivalent in kg)
        - pe: Primary Energy (in kWh)
        - adpe: Abiotic Depletion Potential

    Note:
        - Uses World (WOR) electricity mix as baseline
        - Could be moved to config.py for different regional electricity mixes
        - MoE models use active_params for more accurate inference cost
        - Standard models use total params
    """

    # Extract model parameters
    # Note: Most custom models won't appear in ecologits' database
    # TODO: Contribute custom model data back to ecologits project
    # Alternative approach: could use llm_impacts("huggingface_hub", model_name, token_count, request_latency)
    model_active_parameter_count = get_active_params(model)
    model_total_parameter_count = get_total_params(model)

    # TODO: Move electricity mix zone to config.py for regional customization
    # Currently uses World (WOR) average; could use specific countries (FR, DE, US, etc.)
    electricity_mix_zone = "WOR"
    electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)

    if electricity_mix is None:
        raise ValueError(
            f"ecologits: no electricity_mix for zone '{electricity_mix_zone}' found."
        )

    # Calculate impact using ecologits library
    return compute_llm_impacts(
        model_active_parameter_count=model_active_parameter_count,
        model_total_parameter_count=model_total_parameter_count,
        output_token_count=token_count,
        if_electricity_mix_adpe=electricity_mix.adpe,  # Abiotic Depletion Potential
        if_electricity_mix_pe=electricity_mix.pe,  # Primary Energy
        if_electricity_mix_gwp=electricity_mix.gwp,  # Global Warming Potential (CO2)
        if_electricity_mix_wue=electricity_mix.gwp,  # Use GWP as proxy for water impact
        # Datacenter efficiency parameters (industry average values)
        # PUE: Power Usage Effectiveness (1.0 = perfect, typical hyperscaler ~1.2)
        # WUE: Water Usage Effectiveness (L/kWh, typical ~1.8)
        datacenter_pue=1.2,
        datacenter_wue=1.8,
        request_latency=request_latency,
    )


class Equivalence(TypedDict):
    type: EquivalenceType
    value: float


class Consumption(TypedDict):
    # Token usage
    tokens: int
    # Environmental metrics (CO2)
    co2_kg: int | float
    # Scaled CO2
    scaled_co2_kg: int | float
    scaled_co2_t: int | float
    # Energy metrics
    energy_mwh: int | float
    energy_kwh: int | float
    # Scaled equivalence values
    equivalences: list[Equivalence]


def get_llm_consumption(
    llm: Union["LLMDataRaw", "LLMData"],
    tokens: int,
    request_latency: float | None = None,
    country_portal: CountryPortal = "fr",  # FIXME
) -> Consumption:
    """
    Calculates environmental impact (energy, CO2 emissions)

    Args:
        llm: LLMDataRaw or LLMData with 'params' and optional 'active_params' (MoE)
        token_count: Total output tokens generated
        request_latency: Time taken for inference (optional, for more accurate calculations)

    Returns:
        dict: Consumption
    """
    impact = get_llm_impact(llm, tokens, request_latency)

    # Get raw kWh and CO2 kg values for equivalence calculations
    kwh = convert_range_to_value(impact.energy.value)
    co2_kg = convert_range_to_value(impact.gwp.value)
    # co2 scaled to population using generative AI
    scaled_co2_kg = co2_kg * SCALE_FACTORS[country_portal]

    return {
        "tokens": tokens,
        "co2_kg": co2_kg,
        "scaled_co2_kg": scaled_co2_kg,
        "scaled_co2_t": scaled_co2_kg / 1000,
        "energy_mwh": kwh * 1000 * 1000,
        "energy_kwh": kwh,
        # Compute all equivalences
        "equivalences": [
            {
                "type": eq_type,
                "value": scaled_co2_kg / CO2_KG_EQUIVALENCE[eq_type],
            }
            for eq_type in list(EquivalenceType)
        ],
    }
