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
- calculate_energy_with_unit: Calculates energy consumption
- calculate_co2_with_unit: Calculates CO2 emissions
- get_llm_consumption: Calculates environmental impact
- calculate_scaled_equivalence: Calculate scaled impact metrics
"""

import random
from enum import Enum
from typing import TYPE_CHECKING, TypedDict, Union

from ecologits.impacts import Impacts
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes
from ecologits.utils.range_value import RangeValue, ValueOrRange

if TYPE_CHECKING:
    from backend.llms.models import LLMData
    from utils.models.llms import LLMDataRaw


# Equivalence types for scaled impact comparisons
class EquivalenceType(Enum):
    COUNTRY_ELECTRICITY = "country_electricity"
    CITY_POWER = "city_power"
    EUROPEAN_HOMES = "european_homes"
    NUCLEAR_REACTORS = "nuclear_reactors"
    SOLAR_FARM_AREA = "solar_farm_area"
    WIND_TURBINES = "wind_turbines"
    CAR_EARTH_TRIPS = "car_earth_trips"
    PARIS_NYC_FLIGHTS = "paris_nyc_flights"


# Reference data for scaled equivalences
# Scale: French population (~67 million) using this prompt daily for 1 year
SCALE_FACTOR = 67_000_000 * 365  # ~24.5 billion queries/year

# Country annual electricity consumption in TWh (source: IEA 2023)
COUNTRY_ELECTRICITY_TWH = {
    "france": 470,
    "germany": 500,
    "spain": 260,
    "belgium": 84,
    "netherlands": 110,
    "denmark": 35,
    "sweden": 130,
}

# City daily electricity consumption in GWh/day (estimated from annual consumption)
CITY_ELECTRICITY_GWH_DAY = {
    "paris": 40,
    "amsterdam": 10,
    "copenhagen": 5,
    "stockholm": 8,
}

# European household average annual consumption: 3,500 kWh (source: Eurostat)
EUROPEAN_HOME_KWH_YEAR = 3500

# Nuclear reactor: 1 GW capacity, ~90% uptime = 7,900 GWh/year
NUCLEAR_REACTOR_GWH_YEAR = 7900

# Solar farm: ~150 GWh/year per km² in Europe (source: NREL estimates)
SOLAR_GWH_PER_KM2_YEAR = 150

# Offshore wind turbine: 10 MW, 40% capacity factor = 35 GWh/year
WIND_TURBINE_GWH_YEAR = 35

# Petrol car: ~150g CO2/km average (source: EEA)
CAR_CO2_G_PER_KM = 150

# Earth circumference: 40,075 km
EARTH_CIRCUMFERENCE_KM = 40_075

# Paris-NYC round trip flight: ~1,000 kg CO2 per passenger (source: myclimate.org)
PARIS_NYC_CO2_KG = 1000

# Minimum threshold for meaningful display (values below this aren't intuitive)
MIN_MEANINGFUL_VALUE = 1.0


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


class ValueAndUnit(TypedDict):
    value: int | float
    unit: str


class Consumption(TypedDict):
    # Token usage
    tokens: int
    # Energy (in Wh or mWh)
    energy: ValueAndUnit
    # Environmental metrics (CO2)
    co2: int | float
    # # Energy metrics (deprecated: kept for backward compatibility)
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
    # Get raw kWh and CO2 kg values for equivalence calculations
    kwh = convert_range_to_value(impact.energy.value)
    co2_kg = convert_range_to_value(impact.gwp.value)

    return {
        "tokens": tokens,
        "energy": {"value": energy, "unit": energy_unit},
        "co2": co2_kg,
        "kwh": kwh,
    }


def calculate_scaled_equivalence(conso: Consumption, eq_type: EquivalenceType) -> dict:
    """
    Calculate scaled equivalence for 1 billion daily users over a year.

    Args:
        conso: Consumption per query (energy in kWh, CO2 in kg)
        eq_type: The type of equivalence to calculate

    Returns:
        dict: Contains 'value' (float) representing the scaled metric.
              Frontend will apply locale-specific reference and unit formatting.
    """
    # Scale up to 1 billion users × 365 days
    scaled_energy_kwh = conso["kwh"] * SCALE_FACTOR
    scaled_energy_twh = scaled_energy_kwh / 1e9  # Convert to TWh
    scaled_energy_gwh = scaled_energy_kwh / 1e6  # Convert to GWh
    scaled_co2_kg = conso["co2"] * SCALE_FACTOR
    scaled_co2_tonnes = scaled_co2_kg / 1000

    if eq_type == EquivalenceType.COUNTRY_ELECTRICITY:
        # Return scaled TWh - frontend will divide by country's TWh consumption
        return {"value": scaled_energy_twh}

    elif eq_type == EquivalenceType.CITY_POWER:
        # Return scaled GWh/day - frontend will divide by city's daily consumption
        return {"value": scaled_energy_gwh / 365}  # Convert annual to daily

    elif eq_type == EquivalenceType.EUROPEAN_HOMES:
        # Number of homes that could be powered for a year
        homes = scaled_energy_kwh / EUROPEAN_HOME_KWH_YEAR
        return {"value": homes}

    elif eq_type == EquivalenceType.NUCLEAR_REACTORS:
        # Number of 1 GW reactors needed
        reactors = scaled_energy_gwh / NUCLEAR_REACTOR_GWH_YEAR
        return {"value": reactors}

    elif eq_type == EquivalenceType.SOLAR_FARM_AREA:
        # km² of solar farms needed
        area_km2 = scaled_energy_gwh / SOLAR_GWH_PER_KM2_YEAR
        return {"value": area_km2}

    elif eq_type == EquivalenceType.WIND_TURBINES:
        # Number of 10 MW offshore turbines needed
        turbines = scaled_energy_gwh / WIND_TURBINE_GWH_YEAR
        return {"value": turbines}

    elif eq_type == EquivalenceType.CAR_EARTH_TRIPS:
        # Number of trips around Earth by petrol car
        co2_grams = scaled_co2_kg * 1000
        total_km = co2_grams / CAR_CO2_G_PER_KM
        trips = total_km / EARTH_CIRCUMFERENCE_KM
        return {"value": trips}

    elif eq_type == EquivalenceType.PARIS_NYC_FLIGHTS:
        # Number of Paris-NYC round trip flights
        flights = scaled_co2_kg / PARIS_NYC_CO2_KG
        return {"value": flights}

    else:
        return {"value": 0}


def get_all_meaningful_equivalences(
    conso_a: Consumption,
    conso_b: Consumption,
    seed: int,
) -> list[dict]:
    """
    Get all equivalence types that produce meaningful values for BOTH models.

    This ensures users never see confusing values like "0.01 reactors" - instead
    they'll see more relatable numbers like "15,000 flights" or "2.5 days".

    Algorithm:
        1. Calculate values for all 8 equivalence types for both models
        2. Filter to types where BOTH models produce values >= MIN_MEANINGFUL_VALUE
        3. Shuffle the valid types (using seed for consistency)
        4. If none qualify, include the type with the largest minimum value

    Args:
        conso_a: Consumption for LLM A (energy in kWh, CO2 in kg)
        conso_b: Consumption for LLM B (energy in kWh, CO2 in kg)
        seed: Integer seed for deterministic shuffling

    Returns:
        list[dict]: List of equivalences, each containing:
            - type: The equivalence type string
            - model_a_value: Scaled value for model A
            - model_b_value: Scaled value for model B
    """
    rng = random.Random(seed)

    all_types = list(EquivalenceType)
    valid_equivalences = []
    fallback_equivalence = None
    fallback_min_value = 0

    for eq_type in all_types:
        value_a = calculate_scaled_equivalence(conso_a, eq_type)["value"]
        value_b = calculate_scaled_equivalence(conso_b, eq_type)["value"]
        min_value = min(value_a, value_b)

        equiv_data = {
            "type": eq_type.value,
            "model_a_value": value_a,
            "model_b_value": value_b,
        }

        if min_value >= MIN_MEANINGFUL_VALUE:
            valid_equivalences.append(equiv_data)

        # Track best fallback (type with largest minimum value)
        if min_value > fallback_min_value:
            fallback_min_value = min_value
            fallback_equivalence = equiv_data

    # Shuffle valid equivalences for variety, or use fallback if none qualify
    if valid_equivalences:
        rng.shuffle(valid_equivalences)
        return valid_equivalences
    else:
        return (
            [fallback_equivalence]
            if fallback_equivalence
            else [
                {
                    "type": all_types[0].value,
                    "model_a_value": 0,
                    "model_b_value": 0,
                }
            ]
        )
