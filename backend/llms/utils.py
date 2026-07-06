"""
Environmental impact calculations.

This module computes the ecological impact of LLM inference using the ecologits library,
converting technical metrics (energy, CO2) into user-friendly scaled equivalences
(e.g., "if 1 billion people used this daily for a year").

Functions:
- convert_range_to_value: Normalize impact ranges to single values
- get_total_params: Get the total number of parameters for a LLM
- get_active_params: Get the number of active parameters for a LLM
- get_llm_impact: Calculate environmental impact for a LLM
- get_llm_consumption: Calculates environmental impact
"""

from typing import TYPE_CHECKING, TypedDict

from ecologits.impacts import Impacts
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes
from ecologits.utils.range_value import RangeValue, ValueOrRange

if TYPE_CHECKING:
    from backend.llms.models import APILLMDataBase

# FIXME equivalences legacy?
# from backend.config import CONSUMPTION_SCALE_FACTOR
# # Equivalence types for scaled impact comparisons
# class EquivalenceType(Enum):
#     PARIS_NYC_FLIGHTS = "paris_nyc_flights"
#     BAGUETTE_PRODUCTION = "baguette_production"
#     ONE_YEAR_TREE_ABSORTION = "one_year_tree_absortion"
#     PACKAGE_DELIVERY = "package_delivery"
#     MANGO_IMPORT = "mango_import"
#     POOL_FILING = "pool_filing"


# CO2_KG_EQUIVALENCE: dict[EquivalenceType, float] = {
#     EquivalenceType.PARIS_NYC_FLIGHTS: 0.177894 * 5837,
#     EquivalenceType.BAGUETTE_PRODUCTION: 0.7767000000000001,
#     EquivalenceType.ONE_YEAR_TREE_ABSORTION: 22,
#     EquivalenceType.PACKAGE_DELIVERY: 0.576,
#     EquivalenceType.MANGO_IMPORT: 11.655508000000001,
#     EquivalenceType.POOL_FILING: 7.54,
# }


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


def get_total_params(llm: "APILLMDataBase") -> int:
    """
    Get the total number of parameters for a LLM.

    Accounts for q8 quantization which reduces effective parameters by half.

    Args:
        llm: APILLMDataBase with 'params' and optional 'quantization'

    Returns:
        int: Total parameters, or None if params not available
    """
    # Q8 quantization reduces parameter count (2x compression)
    if llm.quantization == "q8":
        return int(llm.params) // 2
    else:
        return int(llm.params)


def get_active_params(llm: "APILLMDataBase") -> int:
    """
    Get the number of active parameters for a LLM.

    For Mixture of Experts (MoE) LLMs, this is different from total parameters.
    Active params represent how many parameters are used for each token.

    Args:
        llm: APILLMDataBase

    Returns:
        int: Active parameters, or total params if not available
    """
    if llm.active_params:
        # Account for Q8 quantization if present
        if llm.quantization == "q8":
            return int(llm.active_params) // 2
        else:
            return int(llm.active_params)
    else:
        # Fallback to total params if active_params is not available (non-MoE LLMs)
        return get_total_params(llm)


def get_llm_impact(
    llm: "APILLMDataBase",
    token_count: int,
    request_latency: float | None,
) -> Impacts:
    """
    Calculate environmental impact (energy, CO2) for LLM inference.

    Uses the ecologits library to compute impact based on LLM parameters and token usage.
    Currently not all LLMs are in ecologits' database, so this uses estimated parameters instead.

    Args:
        llm: APILLMDataBase with 'params' and optional 'active_params' (MoE)
        tokens: Total output tokens generated
        input_tokens: Total input tokens sent to the model
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
        - MoE LLMs use active_params for more accurate inference cost
        - Standard LLMs use total params
    """

    # Extract LLM parameters
    # Note: Most custom LLMs won't appear in ecologits' database
    # TODO: Contribute custom LLM data back to ecologits project
    # Alternative approach: could use llm_impacts("huggingface_hub", model_name, token_count, request_latency)
    llm_active_parameter_count = get_active_params(llm)
    llm_total_parameter_count = get_total_params(llm)

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
        model_active_parameter_count=llm_active_parameter_count,
        model_total_parameter_count=llm_total_parameter_count,
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


# FIXME equivalences legacy?
# class Equivalence(TypedDict):
# type: EquivalenceType
#     value: float


class Consumption(TypedDict):
    # Token usage
    tokens: int
    input_tokens: int
    total_tokens: int
    # Environmental metrics (CO2)
    co2_kg: int | float
    # Energy metrics
    energy_mwh: int | float
    energy_kwh: int | float
    # FIXME equivalences legacy?
    # # Scaled CO2
    # scaled_co2_kg: int | float
    # scaled_co2_t: int | float
    # # Scaled equivalence values
    # equivalences: list[Equivalence]


def get_llm_consumption(
    llm: "APILLMDataBase",
    tokens: int,
    input_tokens: int = 0,
    request_latency: float | None = None,
) -> Consumption:
    """
    Calculates environmental impact (energy, CO2 emissions)

    Args:
        llm: APILLMDataBase with 'params' and optional 'active_params' (MoE)
        token_count: Total output tokens generated
        request_latency: Time taken for inference (optional, for more accurate calculations)

    Returns:
        dict: Consumption
    """
    impact = get_llm_impact(llm, tokens, request_latency)

    # Get raw kWh and CO2 kg values for equivalence calculations
    kwh = convert_range_to_value(impact.energy.value)
    co2_kg = convert_range_to_value(impact.gwp.value)
    # FIXME equivalences legacy?
    # co2 scaled to population using generative AI
    # scaled_co2_kg = co2_kg * CONSUMPTION_SCALE_FACTOR

    return {
        "tokens": tokens,
        "input_tokens": input_tokens,
        "total_tokens": input_tokens + tokens,
        "co2_kg": co2_kg,
        "energy_mwh": kwh * 1000 * 1000,
        "energy_kwh": kwh,
        # FIXME equivalences legacy?
        # "scaled_co2_kg": scaled_co2_kg,
        # "scaled_co2_t": scaled_co2_kg / 1000,
        # Compute all equivalences
        # "equivalences": [
        #     {
        #         "type": eq_type,
        #         "value": scaled_co2_kg / CO2_KG_EQUIVALENCE[eq_type],
        #     }
        #     for eq_type in list(EquivalenceType)
        # ],
    }
