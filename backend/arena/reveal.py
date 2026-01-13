"""
Environmental impact calculations and reveal screen data generation.

This module computes the ecological impact of LLM inference using the ecologits library,
converting technical metrics (energy, CO2) into user-friendly comparisons (LED lightbulbs, video streaming).

Functions:
- convert_range_to_value: Normalize impact ranges to single values
- calculate_lightbulb_consumption: Energy equivalent in LED light hours
- calculate_streaming_hours: CO2 equivalent in video streaming hours
- get_reveal_data: Main function generating reveal screen data
"""

import logging

from backend.arena.models import BotChoice, BotPos, Conversations, RevealData
from backend.arena.utils import sum_tokens
from backend.language_models.utils import (
    calculate_lightbulb_consumption,
    calculate_streaming_hours,
    convert_range_to_value,
    get_llm_consumption,
    get_llm_impact,
)

logger = logging.getLogger("languia")


def get_chosen_llm(conversations: Conversations) -> BotChoice | None:
    if conversations.vote:
        return conversations.vote.chosen_llm

    reactions: dict[BotPos, dict[int, bool]] = {
        "a": {r.index: r.liked for r in conversations.conversation_a.reactions},
        "b": {r.index: r.liked for r in conversations.conversation_b.reactions},
    }

    indexes: set[int] = set([*reactions["a"].keys(), *reactions["b"].keys()])

    if not indexes:
        # No reactions
        return None

    scores = {"a": 0, "b": 0}
    for index in indexes:
        for pos in ("a", "b"):
            liked = reactions[pos].get(index, None)
            if liked is not None:
                scores[pos] += 1 if liked else -1

    if scores["a"] > scores["b"]:
        return "a"
    elif scores["b"] > scores["a"]:
        return "b"
    else:
        return "both_equal"


def get_reveal_data(conversations: Conversations, chosen_llm: BotChoice) -> RevealData:
    """
    Build reveal screen data with model comparison and environmental impact metrics.

    Calculates environmental impact (energy, CO2 emissions) and creates data for the
    reveal screen shown after voting. Includes model metadata, token counts, and
    user-friendly comparisons (LED lightbulb hours, video streaming equivalents).

    Args:
        conversations: Conversation object for model B with messages and model_name
        chosen_llm: User's choice ("a", "b", or "both_equal")

    Returns:
        dict: RevealData containing:
            - b64: Base64-encoded JSON summary (compact storage/transmission)
            - chosen_llm: User's model preference ("a", "b" or None)
            - a: llm 'a' data (see `LanguageModel`) and conso (see `Consumption`)
            - b: llm 'b' data (see `LanguageModel`) and conso (see `Consumption`)

    Process:
        1. Compute total output tokens for each conversation
        2. Compute `Consumption` data for each conversation
        3. Encode summary to base64 for efficient storage
        4. Return comprehensive metrics for reveal screen display
    """
    import base64
    import json

    # TODO: Add request_latency for more accurate impact calculations
    # Currently not tracked; would need start/finish timestamps from Conversation
    # Compute it for each exchange (user prompt/llm response)
    # request_latency = conv.finish_tstamp - conv.start_tstamp
    # Calculate environmental impact using ecologits library
    # Uses llm params, active params (for MoE) and token count
    conv_a = conversations.conversation_a
    tokens_a = conv_a.tokens
    conso_a = get_llm_consumption(conv_a.llm, tokens_a)
    logger.debug(f"[REVEAL] output_tokens (llm 'a'): {tokens_a}")
    conv_b = conversations.conversation_b
    tokens_b = conv_b.tokens
    conso_b = get_llm_consumption(conv_b.llm, tokens_b)
    logger.debug(f"[REVEAL] output_tokens (llm 'b'): {tokens_b}")

    # Encode summary as base64 for safe storage/transmission (share feature)
    jsonstring = json.dumps(
        {
            "a": conv_a.model_name,  # Model A identifier
            "b": conv_b.model_name,  # Model B identifier
            "ta": tokens_a,  # Model A token count
            "tb": tokens_b,  # Model B token count
            # Add user's choice to summary (for verification/tracking)
            "c": chosen_llm,
        }
    ).encode("ascii")
    b64 = base64.b64encode(jsonstring).decode("ascii")

    # Return comprehensive reveal data for frontend display
    return {
        "b64": b64,
        "chosen_llm": chosen_llm,
        "a": {"llm": conv_a.llm, "conso": conso_a},
        "b": {"llm": conv_b.llm, "conso": conso_b},
    }
