import logging
from typing import TYPE_CHECKING

from ecologits.impacts import Impacts
from ecologits.tracers.utils import compute_llm_impacts, electricity_mixes
from ecologits.utils.range_value import RangeValue, ValueOrRange

if TYPE_CHECKING:
    from backend.models.models import Model

logger = logging.getLogger("languia")


def filter_enabled_models(models: dict[str, "Model"]):
    from backend.models.models import Endpoint

    enabled_models = {}
    for model_id, model_dict in models.items():
        if model_dict.get("status") == "enabled":
            try:
                if Endpoint.model_validate(model_dict.get("endpoint")):
                    enabled_models[model_id] = model_dict
            except:
                continue

    return enabled_models


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


def get_total_params(model_extra_info) -> int | None:
    """
    Get the total number of parameters for a model.

    Accounts for q8 quantization which reduces effective parameters by half.

    Args:
        model_extra_info: Dict containing model metadata with 'params' and optional 'quantization'

    Returns:
        int: Total parameters, or None if params not available
    """
    if model_extra_info.get("params"):
        # Q8 quantization reduces parameter count (2x compression)
        if model_extra_info.get("quantization", None) == "q8":
            return int(model_extra_info["params"]) // 2
        else:
            return int(model_extra_info["params"])
    else:
        logger.error(
            f"Couldn't get total params for {model_extra_info.get('id')}, missing params"
        )
        return None


def get_active_params(model_extra_info) -> int | None:
    """
    Get the number of active parameters for a model.

    For Mixture of Experts (MoE) models, this is different from total parameters.
    Active params represent how many parameters are used for each token.

    Args:
        model_extra_info: Dict containing model metadata

    Returns:
        int: Active parameters, or total params if not available
    """
    if model_extra_info.get("active_params"):
        # Account for Q8 quantization if present
        if model_extra_info.get("quantization", None) == "q8":
            return int(model_extra_info["active_params"]) // 2
        else:
            return int(model_extra_info["active_params"])
    else:
        # Fallback to total params if active_params is not available (non-MoE models)
        return get_total_params(model_extra_info)


def get_llm_impact(
    model_extra_info: dict,
    model_name: str,
    token_count: int,
    request_latency: float | None,
) -> Impacts | None:
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

    if electricity_mix is None:
        # FIXME raise error?
        return None

    # Extract electricity mix components for impact calculation
    if_electricity_mix_adpe = electricity_mix.adpe  # Abiotic Depletion Potential
    if_electricity_mix_pe = electricity_mix.pe  # Primary Energy
    if_electricity_mix_gwp = electricity_mix.gwp  # Global Warming Potential (CO2)

    # Calculate impact using ecologits library
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
