import logging
from languia.utils import sum_tokens, get_active_params, get_total_params

from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes


def convert_range_to_value(value_or_range):

    if hasattr(value_or_range, "min"):
        return (value_or_range.min + value_or_range.max) / 2
    else:
        return value_or_range


def calculate_lightbulb_consumption(impact_energy_value):
    """
    Calculates the energy consumption of a 5W LED light and determines the most sensible time unit.

    Args:
      impact_energy_value: Energy consumption in kilowatt-hours (kWh).

    Returns:
      A tuple containing:
        - An integer representing the consumption time.
        - A string representing the most sensible time unit ('days', 'hours', 'minutes', or 'seconds').
    """
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
    else:
        return int(consumption_seconds), "s"


def calculate_streaming_hours(impact_gwp_value_or_range):
    """
    Calculates equivalent streaming hours and determines a sensible time unit.

    Args:
      impact_gwp_value: CO2 emissions in kilograms.

    Returns:
      A tuple containing:
        - An integer representing the streaming hours.
        - A string representing the most sensible time unit ('days', 'hours', 'minutes', or 'seconds').
    """

    if hasattr(impact_gwp_value_or_range, "min"):
        impact_gwp_value = (
            impact_gwp_value_or_range.min + impact_gwp_value_or_range.max
        ) / 2
    else:
        impact_gwp_value = impact_gwp_value_or_range
    # Calculate streaming hours: https://impactco2.fr/outils/usagenumerique/streamingvideo
    streaming_hours = (impact_gwp_value * 10000) / 317

    # Determine sensible unit based on magnitude
    if streaming_hours >= 24:  # 1 day in hours
        return int(streaming_hours / 24), "j"
    elif streaming_hours >= 1:
        return int(streaming_hours), "h"
    elif streaming_hours * 60 >= 1:
        return int(streaming_hours * 60), "min"
    else:
        return int(streaming_hours * 60 * 60), "s"


def build_reveal_dict(conv_a, conv_b, chosen_model):
    from languia.config import all_models_data

    logger = logging.getLogger("languia")

    model_a = all_models_data["models"].get(conv_a.model_name)
    model_b = all_models_data["models"].get(conv_b.model_name)

    model_a_tokens = sum_tokens(conv_a.messages)
    logger.debug("output_tokens (model a): " + str(model_a_tokens))

    model_b_tokens = sum_tokens(conv_b.messages)
    logger.debug("output_tokens (model b): " + str(model_b_tokens))

    # TODO:
    # request_latency_a = conv_a.conv.finish_tstamp - conv_a.conv.start_tstamp
    # request_latency_b = conv_b.conv.finish_tstamp - conv_b.conv.start_tstamp
    model_a_impact = get_llm_impact(model_a, conv_a.model_name, model_a_tokens, None)
    model_b_impact = get_llm_impact(model_b, conv_b.model_name, model_b_tokens, None)

    model_a_kwh = convert_range_to_value(model_a_impact.energy.value)
    model_b_kwh = convert_range_to_value(model_b_impact.energy.value)
    model_a_co2 = convert_range_to_value(model_a_impact.gwp.value)
    model_b_co2 = convert_range_to_value(model_b_impact.gwp.value)
    lightbulb_a, lightbulb_a_unit = calculate_lightbulb_consumption(model_a_kwh)
    lightbulb_b, lightbulb_b_unit = calculate_lightbulb_consumption(model_b_kwh)

    streaming_a, streaming_a_unit = calculate_streaming_hours(model_a_co2)
    streaming_b, streaming_b_unit = calculate_streaming_hours(model_b_co2)

    import base64, json

    data = {
        "a": conv_a.model_name,
        "b": conv_b.model_name,
        "ta": model_a_tokens,
        "tb": model_b_tokens,
    }
    if chosen_model == "model-a":
        data["c"] = "a"
    elif chosen_model == "model-b":
        data["c"] = "b"

    jsonstring = json.dumps(data).encode("ascii")
    b64 = base64.b64encode(jsonstring).decode("ascii")

    return dict(
        b64=b64,
        model_a=model_a,
        model_b=model_b,
        chosen_model=chosen_model,
        model_a_kwh=model_a_kwh,
        model_b_kwh=model_b_kwh,
        model_a_co2=model_a_co2,
        model_b_co2=model_b_co2,
        model_a_tokens=model_a_tokens,
        model_b_tokens=model_b_tokens,
        streaming_a=streaming_a,
        streaming_a_unit=streaming_a_unit,
        streaming_b=streaming_b,
        streaming_b_unit=streaming_b_unit,
        lightbulb_a=lightbulb_a,
        lightbulb_a_unit=lightbulb_a_unit,
        lightbulb_b=lightbulb_b,
        lightbulb_b_unit=lightbulb_b_unit,
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
    """Compute or fallback to estimated impact for an LLM."""
    logger = logging.getLogger("languia")
    # most of the time, won't appear in venv/lib64/python3.11/site-packages/ecologits/data/models.csv, should use compute_llm_impacts instead
    # TODO: contribute back to that list
    # impact = llm_impacts("huggingface_hub", model_name, token_count, request_latency)
    model_active_parameter_count = get_active_params(model_extra_info)
    model_total_parameter_count = get_total_params(model_extra_info)

    if not model_active_parameter_count or not model_total_parameter_count:
        logger.error("Couldn't calculate impact for" + model_name + ", missing params")
        return None

    # TODO: move to config.py
    electricity_mix_zone = "WOR"
    electricity_mix = electricity_mixes.find_electricity_mix(zone=electricity_mix_zone)
    if_electricity_mix_adpe = electricity_mix.adpe
    if_electricity_mix_pe = electricity_mix.pe
    if_electricity_mix_gwp = electricity_mix.gwp

    impact = compute_llm_impacts(
        model_active_parameter_count=model_active_parameter_count,
        model_total_parameter_count=model_total_parameter_count,
        output_token_count=token_count,
        if_electricity_mix_adpe=if_electricity_mix_adpe,
        if_electricity_mix_pe=if_electricity_mix_pe,
        if_electricity_mix_gwp=if_electricity_mix_gwp,
        request_latency=request_latency,
    )
    return impact
