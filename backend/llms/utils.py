from typing import TYPE_CHECKING, TypedDict, Union

from ecologits.impacts import Impacts
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes
from ecologits.utils.range_value import RangeValue, ValueOrRange

if TYPE_CHECKING:
    from backend.llms.models import LLMData
    from utils.models.llms import LLMDataRaw


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
        if_electricity_mix_wue=electricity_mix.wue,  # Water Consumption Factor (L/kWh)
        # Data center efficiency metrics (from ecologits 0.9.2 methodology)
        # PUE = 1.15 (average of major providers: Google 1.09, Anthropic 1.09-1.14, Mistral 1.16, OpenAI 1.20)
        # WUE = 1.8 L/kWh (required parameter, not displayed to users)
        datacenter_pue=1.15,
        datacenter_wue=1.8,
        request_latency=request_latency,
    )


def calculate_energy_with_unit(impact_energy_value_or_range):
    """
    Calculates energy consumption and determines the most sensible unit.

    Args:
      impact_energy_value_or_range: Energy consumption in kilowatt-hours (kWh).

    Returns:
      A tuple containing:
        - A float representing the energy value.
        - A string representing the most sensible unit ('Wh' or 'mWh').
    """
    impact_energy_value = convert_range_to_value(impact_energy_value_or_range)

    # Convert to watt-hours
    energy_wh = impact_energy_value * 1000

    # Determine sensible unit based on magnitude
    if energy_wh >= 1:
        return energy_wh, "Wh"
    else:
        # Convert to milliwatt-hours for very small values
        energy_mwh = energy_wh * 1000
        return energy_mwh, "mWh"


def calculate_co2_with_unit(
    impact_gwp_value_or_range: ValueOrRange,
) -> tuple[int | float, str]:
    """
    Calculates CO2 emissions and determines the most sensible unit.

    Args:
      impact_gwp_value_or_range: CO2 emissions in kilograms.

    Returns:
      A tuple containing:
        - A float representing the CO2 value.
        - A string representing the most sensible unit ('kg', 'g', or 'mg').
    """
    impact_gwp_value = convert_range_to_value(impact_gwp_value_or_range)

    # Convert to grams
    co2_grams = impact_gwp_value * 1000

    # Determine sensible unit based on magnitude
    if co2_grams >= 1:
        return co2_grams, "g"
    else:
        # Convert to milligrams for very small values
        co2_milligrams = co2_grams * 1000
        return co2_milligrams, "mg"


def calculate_lightbulb_consumption(
    impact_energy_value_or_range: ValueOrRange,
) -> tuple[int | float, str]:
    """
    Calculates the energy consumption of a 5W LED light and determines the most sensible time unit.

    Args:
      impact_energy_value: Energy consumption in kilowatt-hours (kWh).

    Returns:
      A tuple containing:
        - A number representing the consumption time.
        - A string representing the most sensible time unit ('j', 'h', 'min', 's', or 'ms').
    """
    impact_energy_value = convert_range_to_value(impact_energy_value_or_range)
    # Calculate consumption time using Wh
    watthours = impact_energy_value * 1000
    consumption_hours = watthours / 5
    consumption_days = watthours / (5 * 24)
    consumption_minutes = watthours * 60 / (5)
    consumption_seconds = watthours * 60 * 60 / (5)

    # Determine the most sensible unit based on magnitude
    if consumption_days >= 1:
        return int(consumption_days), "j"
    elif consumption_hours >= 1:
        return int(consumption_hours), "h"
    elif consumption_minutes >= 1:
        return int(consumption_minutes), "min"
    elif consumption_seconds >= 1:
        return int(consumption_seconds), "s"
    else:
        # For very small values, use milliseconds
        consumption_milliseconds = watthours * 60 * 60 * 1000 / 5
        return round(consumption_milliseconds, 2), "ms"


def calculate_streaming_hours(
    impact_gwp_value_or_range: ValueOrRange,
) -> tuple[int | float, str]:
    """
    Calculates equivalent streaming hours and determines a sensible time unit.

    Args:
      impact_gwp_value: CO2 emissions in kilograms.

    Returns:
      A tuple containing:
        - A number representing the streaming time.
        - A string representing the most sensible time unit ('j', 'h', 'min', 's', or 'ms').
    """
    impact_gwp_value = convert_range_to_value(impact_gwp_value_or_range)
    # Calculate streaming hours: https://impactco2.fr/outils/usagenumerique/streamingvideo
    streaming_hours = (impact_gwp_value * 10000) / 317

    # Determine sensible unit based on magnitude
    if streaming_hours >= 24:  # 1 day in hours
        return int(streaming_hours / 24), "j"
    elif streaming_hours >= 1:
        return int(streaming_hours), "h"
    elif streaming_hours * 60 >= 1:
        return int(streaming_hours * 60), "min"
    elif streaming_hours * 60 * 60 >= 1:
        return int(streaming_hours * 60 * 60), "s"
    else:
        # For very small values, use milliseconds
        return round(streaming_hours * 60 * 60 * 1000, 2), "ms"


class ValueAndUnit(TypedDict):
    value: int | float
    unit: str


class Consumption(TypedDict):
    # Token usage
    tokens: int
    # Energy (in Wh or mWh)
    energy: ValueAndUnit
    # Environmental metrics (CO2)
    co2: ValueAndUnit
    # Video streaming equivalent (user-friendly CO2 comparison)
    streaming: ValueAndUnit
    # LED lightbulb equivalent (user-friendly energy comparison)
    lightbulb: ValueAndUnit
    # Energy metrics (deprecated: kept for backward compatibility)
    kwh: int | float


def get_llm_consumption(
    llm: Union["LLMDataRaw", "LLMData"],
    tokens: int,
    request_latency: float | None = None,
) -> Consumption:
    """
    Calculates environmental impact (energy, CO2 emissions)

    Args:
        llm: LLMDataRaw or LLMData with 'params' and optional 'active_params' (MoE)
        token_count: Total output tokens generated
        request_latency: Time taken for inference (optional, for more accurate calculations)

    Returns:

    """
    impact = get_llm_impact(llm, tokens, request_latency)

    # Convert energy to appropriate unit (Wh or mWh) with dynamic unit selection
    energy, energy_unit = calculate_energy_with_unit(impact.energy.value)
    # Convert CO2 to appropriate unit (g or mg) with dynamic unit selection
    co2, co2_unit = calculate_co2_with_unit(impact.gwp.value)
    # Keep kWh for backward compatibility with lightbulb calculation
    kwh = convert_range_to_value(impact.energy.value)

    # Convert energy to LED lightbulb comparison (5W LED light)
    lightbulb, lightbulb_unit = calculate_lightbulb_consumption(kwh)
    # Convert CO2 to video streaming comparison
    streaming, streaming_unit = calculate_streaming_hours(impact.gwp.value)

    return {
        "tokens": tokens,
        "energy": {"value": energy, "unit": energy_unit},
        "co2": {"value": co2, "unit": co2_unit},
        "lightbulb": {"value": lightbulb, "unit": lightbulb_unit},
        "streaming": {"value": streaming, "unit": streaming_unit},
        # Deprecated: kept for backward compatibility
        "kwh": kwh,
    }
