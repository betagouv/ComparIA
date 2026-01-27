"""
Environmental impact calculations and reveal screen data generation.

This module computes the ecological impact of LLM inference using the ecologits library,
converting technical metrics (energy, CO2) into user-friendly scaled equivalences
(e.g., "if 1 billion people used this daily for a year").

Functions:
- convert_range_to_value: Normalize impact ranges to single values
- get_equivalence_seed: Generate deterministic seed from conversation IDs
- select_equivalence_type: Randomly select equivalence type using seed
- calculate_scaled_equivalence: Calculate scaled impact metrics
- build_reveal_dict: Main function generating reveal screen data
- determine_choice_badge: Infer user preference from message reactions
- get_llm_impact: Calculate environmental impact for a model
"""

import logging
import random
from enum import Enum
from languia.utils import sum_tokens, get_active_params, get_total_params

from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes


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
    FOREST_ABSORPTION = "forest_absorption"
    TREES_PLANTED = "trees_planted"
    CARBON_BUDGET = "carbon_budget"
    TGV_PARIS_LYON = "tgv_paris_lyon"


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

# Forest CO2 absorption: ~8 tonnes CO2/ha/year for mature temperate forest
# Source: ONF (Office National des Forêts), INRAE
FOREST_CO2_TONNES_PER_HA_YEAR = 8

# Tree CO2 absorption: ~15 kg CO2/year average over 10 years (young tree)
# Source: European Environment Agency
TREE_CO2_KG_PER_10_YEARS = 150

# Annual carbon footprint per person in kg CO2
# Source: Ministère de la Transition Écologique
CARBON_BUDGET_KG = {
    "france": 9000,
    "germany": 8000,
    "denmark": 5500,
    "sweden": 4500,
}

# TGV Paris-Lyon: ~4 kg CO2 per passenger (~500 km)
# Source: SNCF environmental reports
TGV_PARIS_LYON_CO2_KG = 4

# Minimum threshold for meaningful display (values below this aren't intuitive)
MIN_MEANINGFUL_VALUE = 1.0


def convert_range_to_value(value_or_range):
    """
    Convert impact range to a single representative value.

    Some impacts are returned as ranges [min, max]; this takes the average.
    Single values are returned as-is.

    Args:
        value_or_range: Either a range object with min/max attributes or a scalar value

    Returns:
        float: Average of range, or the value itself if scalar
    """

    if hasattr(value_or_range, "min"):
        return (value_or_range.min + value_or_range.max) / 2
    else:
        return value_or_range


def get_equivalence_seed(conv_a_id: str, conv_b_id: str) -> int:
    """
    Generate a deterministic seed from conversation IDs.

    This ensures the same equivalence type is shown for both models
    in the same conversation, while being random across different conversations.

    Args:
        conv_a_id: Conversation ID for model A
        conv_b_id: Conversation ID for model B

    Returns:
        int: A 32-bit seed for random selection
    """
    combined = conv_a_id + conv_b_id
    return hash(combined) % (2**32)


def get_all_meaningful_equivalences(
    energy_a_kwh: float, co2_a_kg: float,
    energy_b_kwh: float, co2_b_kg: float,
    seed: int
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
        energy_a_kwh: Energy consumption for model A in kWh
        co2_a_kg: CO2 emissions for model A in kg
        energy_b_kwh: Energy consumption for model B in kWh
        co2_b_kg: CO2 emissions for model B in kg
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
        value_a = calculate_scaled_equivalence(energy_a_kwh, co2_a_kg, eq_type)["value"]
        value_b = calculate_scaled_equivalence(energy_b_kwh, co2_b_kg, eq_type)["value"]
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
        return [fallback_equivalence] if fallback_equivalence else [{
            "type": all_types[0].value,
            "model_a_value": 0,
            "model_b_value": 0,
        }]


def calculate_scaled_equivalence(energy_kwh: float, co2_kg: float, eq_type: EquivalenceType) -> dict:
    """
    Calculate scaled equivalence for 1 billion daily users over a year.

    Args:
        energy_kwh: Energy consumption per query in kWh
        co2_kg: CO2 emissions per query in kg
        eq_type: The type of equivalence to calculate

    Returns:
        dict: Contains 'value' (float) representing the scaled metric.
              Frontend will apply locale-specific reference and unit formatting.
    """
    # Scale up to 1 billion users × 365 days
    scaled_energy_kwh = energy_kwh * SCALE_FACTOR
    scaled_energy_twh = scaled_energy_kwh / 1e9  # Convert to TWh
    scaled_energy_gwh = scaled_energy_kwh / 1e6  # Convert to GWh
    scaled_co2_kg = co2_kg * SCALE_FACTOR
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

    elif eq_type == EquivalenceType.FOREST_ABSORPTION:
        # Hectares of forest absorbing CO2 for one year
        hectares = scaled_co2_tonnes / FOREST_CO2_TONNES_PER_HA_YEAR
        return {"value": hectares}

    elif eq_type == EquivalenceType.TREES_PLANTED:
        # Trees growing for 10 years to absorb this CO2
        trees = scaled_co2_kg / TREE_CO2_KG_PER_10_YEARS
        return {"value": trees}

    elif eq_type == EquivalenceType.CARBON_BUDGET:
        # Return scaled CO2 in kg - frontend divides by locale's per-capita budget
        return {"value": scaled_co2_kg}

    elif eq_type == EquivalenceType.TGV_PARIS_LYON:
        # Number of TGV Paris-Lyon journeys
        journeys = scaled_co2_kg / TGV_PARIS_LYON_CO2_KG
        return {"value": journeys}

    else:
        return {"value": 0}


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
    if hasattr(impact_energy_value_or_range, "min"):
        impact_energy_value = (
            impact_energy_value_or_range.min + impact_energy_value_or_range.max
        ) / 2
    else:
        impact_energy_value = impact_energy_value_or_range

    # Convert to watt-hours
    energy_wh = impact_energy_value * 1000

    # Determine sensible unit based on magnitude
    if energy_wh >= 1:
        return energy_wh, "Wh"
    else:
        # Convert to milliwatt-hours for very small values
        energy_mwh = energy_wh * 1000
        return energy_mwh, "mWh"


def calculate_co2_with_unit(impact_gwp_value_or_range):
    """
    Calculates CO2 emissions and determines the most sensible unit.

    Args:
      impact_gwp_value_or_range: CO2 emissions in kilograms.

    Returns:
      A tuple containing:
        - A float representing the CO2 value.
        - A string representing the most sensible unit ('kg', 'g', or 'mg').
    """
    if hasattr(impact_gwp_value_or_range, "min"):
        impact_gwp_value = (
            impact_gwp_value_or_range.min + impact_gwp_value_or_range.max
        ) / 2
    else:
        impact_gwp_value = impact_gwp_value_or_range

    # Convert to grams
    co2_grams = impact_gwp_value * 1000

    # Determine sensible unit based on magnitude
    if co2_grams >= 1:
        return co2_grams, "g"
    else:
        # Convert to milligrams for very small values
        co2_milligrams = co2_grams * 1000
        return co2_milligrams, "mg"


def build_reveal_dict(conv_a, conv_b, chosen_model):
    """
    Build reveal screen data with model comparison and environmental impact metrics.

    Calculates environmental impact (energy, CO2 emissions) and creates data for the
    reveal screen shown after voting. Includes model metadata, token counts, and
    scaled equivalence (e.g., "if 1 billion people used this daily for a year").

    Args:
        conv_a: Conversation object for model A with messages, model_name, and conv_id
        conv_b: Conversation object for model B with messages, model_name, and conv_id
        chosen_model: User's choice ("model-a", "model-b", or other for no choice)

    Returns:
        dict: Reveal data containing:
            - b64: Base64-encoded JSON summary (compact storage/transmission)
            - model_a/model_b: Full model metadata dicts
            - chosen_model: User's model preference
            - model_a/b_energy + unit: Energy consumption with dynamic units
            - model_a/b_tokens: Total output tokens generated by each model
            - equivalence_type: Type of scaled equivalence (same for both models)
            - model_a/b_equivalence_value: Scaled value for each model

    Process:
        1. Load model definitions from config
        2. Calculate total output tokens for each conversation
        3. Compute environmental impact using ecologits library
        4. Select random equivalence type (seeded by conversation IDs for consistency)
        5. Calculate scaled equivalence values for both models
        6. Encode summary to base64 for efficient storage
        7. Return comprehensive metrics for reveal screen display
    """
    from languia.config import all_models_data

    logger = logging.getLogger("languia")

    # Load complete model metadata from config
    model_a = all_models_data["models"].get(conv_a.model_name)
    model_b = all_models_data["models"].get(conv_b.model_name)

    # Calculate total tokens generated by each model
    model_a_tokens = sum_tokens(conv_a.messages)
    logger.debug("output_tokens (model a): " + str(model_a_tokens))

    model_b_tokens = sum_tokens(conv_b.messages)
    logger.debug("output_tokens (model b): " + str(model_b_tokens))

    # TODO: Add request_latency for more accurate impact calculations
    # Currently not tracked; would need start/finish timestamps from conversations
    # request_latency_a = conv_a.conv.finish_tstamp - conv_a.conv.start_tstamp
    # request_latency_b = conv_b.conv.finish_tstamp - conv_b.conv.start_tstamp

    # Calculate environmental impact using ecologits library
    # Uses model parameters, active parameters (for MoE), and token count
    model_a_impact = get_llm_impact(model_a, conv_a.model_name, model_a_tokens, None)
    model_b_impact = get_llm_impact(model_b, conv_b.model_name, model_b_tokens, None)

    # Convert energy to appropriate unit (Wh or mWh) with dynamic unit selection
    model_a_energy, model_a_energy_unit = calculate_energy_with_unit(model_a_impact.energy.value)
    model_b_energy, model_b_energy_unit = calculate_energy_with_unit(model_b_impact.energy.value)

    # Get raw kWh and CO2 kg values for equivalence calculations
    model_a_kwh = convert_range_to_value(model_a_impact.energy.value)
    model_b_kwh = convert_range_to_value(model_b_impact.energy.value)
    model_a_co2_kg = convert_range_to_value(model_a_impact.gwp.value)
    model_b_co2_kg = convert_range_to_value(model_b_impact.gwp.value)

    # Get all meaningful equivalences for both models
    # Uses conversation IDs as seed for consistent shuffling across page refreshes
    seed = get_equivalence_seed(conv_a.conv_id, conv_b.conv_id)
    equivalences = get_all_meaningful_equivalences(
        model_a_kwh, model_a_co2_kg,
        model_b_kwh, model_b_co2_kg,
        seed
    )

    import base64, json

    # Create compact summary for encoding
    data = {
        "a": conv_a.model_name,  # Model A identifier
        "b": conv_b.model_name,  # Model B identifier
        "ta": model_a_tokens,    # Model A token count
        "tb": model_b_tokens,    # Model B token count
    }

    # Add user's choice to summary (for verification/tracking)
    if chosen_model == "model-a":
        data["c"] = "a"
    elif chosen_model == "model-b":
        data["c"] = "b"

    # Encode summary as base64 for safe storage/transmission
    jsonstring = json.dumps(data).encode("ascii")
    b64 = base64.b64encode(jsonstring).decode("ascii")

    # Return comprehensive reveal data for frontend display
    return dict(
        b64=b64,  # Encoded summary
        model_a=model_a,  # Full model A metadata
        model_b=model_b,  # Full model B metadata
        chosen_model=chosen_model,  # User's preference
        # Energy metrics with dynamic units (Wh or mWh)
        model_a_energy=model_a_energy,
        model_a_energy_unit=model_a_energy_unit,
        model_b_energy=model_b_energy,
        model_b_energy_unit=model_b_energy_unit,
        # Token usage
        model_a_tokens=model_a_tokens,
        model_b_tokens=model_b_tokens,
        # All meaningful scaled equivalences (frontend can cycle through them)
        # Each contains: type, model_a_value, model_b_value
        equivalences=equivalences,
    )


def determine_choice_badge(reactions):
    your_choice_badge = None
    reactions = [reaction for reaction in reactions if reaction]
    # Case: Only one reaction exists
    if len(reactions) == 1:

        print("reaction")
        print(reactions)
        if reactions[0].get("liked") == True:
            # Assign "a" if the reaction is for the first message
            your_choice_badge = (
                "model-a" if reactions[0].get("index") == 1 else "model-b"
            )

    # Case: Two reactions exist
    elif len(reactions) == 2:
        print("reactions")
        print(reactions)

        # Ensure one reaction is "liked" and the other is different
        if (
            reactions[0].get("liked") == True
            and reactions[0].get("liked") != reactions[1].get("liked")
        ) or (
            reactions[1].get("liked") == True
            and reactions[1].get("liked") != reactions[0].get("liked")
        ):
            # Assign "a" or "b" based on the liked reaction's index
            your_choice_badge = (
                "model-a"
                if reactions[0]["liked"] and reactions[0].get("index") == 1
                else "model-b"
            )

    return your_choice_badge


def get_llm_impact(
    model_extra_info, model_name: str, token_count: int, request_latency: float
) -> dict:
    """
    Calculate environmental impact (energy, CO2) for LLM inference.

    Uses the ecologits library to compute impact based on model parameters and token usage.
    Currently not all models are in ecologits' database, so this uses estimated parameters instead.

    Args:
        model_extra_info: Model metadata dict with 'params' and optional 'active_params' (MoE)
        model_name: Model identifier for logging
        token_count: Total output tokens generated
        request_latency: Time taken for inference (optional, for more accurate calculations)

    Returns:
        Impact object with .energy.value and .gwp.value (CO2) attributes
        Returns None if model parameters are missing

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
    logger = logging.getLogger("languia")

    # Extract model parameters
    # Note: Most custom models won't appear in ecologits' database
    # TODO: Contribute custom model data back to ecologits project
    # Alternative approach: could use llm_impacts("huggingface_hub", model_name, token_count, request_latency)
    model_active_parameter_count = get_active_params(model_extra_info)
    model_total_parameter_count = get_total_params(model_extra_info)

    # Validate that we have necessary parameters
    if not model_active_parameter_count or not model_total_parameter_count:
        logger.error("Couldn't calculate impact for" + model_name + ", missing params")
        return None

    # TODO: Move electricity mix zone to config.py for regional customization
    # Currently uses World (WOR) average; could use specific countries (FR, DE, US, etc.)
    electricity_mix_zone = "WOR"
    electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)

    # Extract electricity mix components for impact calculation
    if_electricity_mix_adpe = electricity_mix.adpe    # Abiotic Depletion Potential
    if_electricity_mix_pe = electricity_mix.pe        # Primary Energy
    if_electricity_mix_gwp = electricity_mix.gwp      # Global Warming Potential (CO2)

    # Datacenter efficiency parameters (industry average values)
    # PUE: Power Usage Effectiveness (1.0 = perfect, typical hyperscaler ~1.2)
    # WUE: Water Usage Effectiveness (L/kWh, typical ~1.8)
    datacenter_pue = 1.2
    datacenter_wue = 1.8
    if_electricity_mix_wue = electricity_mix.gwp  # Use GWP as proxy for water impact

    # Calculate impact using ecologits library
    impact = compute_llm_impacts(
        model_active_parameter_count=model_active_parameter_count,
        model_total_parameter_count=model_total_parameter_count,
        output_token_count=token_count,
        if_electricity_mix_adpe=if_electricity_mix_adpe,
        if_electricity_mix_pe=if_electricity_mix_pe,
        if_electricity_mix_gwp=if_electricity_mix_gwp,
        if_electricity_mix_wue=if_electricity_mix_wue,
        datacenter_pue=datacenter_pue,
        datacenter_wue=datacenter_wue,
        request_latency=request_latency,
    )
    return impact
