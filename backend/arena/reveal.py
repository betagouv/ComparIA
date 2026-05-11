"""
Reveal screen data generation.

Functions:
- get_chosen_llm: Compute the chosen LLM
- get_reveal_data: Main function generating reveal screen data
"""

import logging
from typing import TypedDict

from backend.arena.models import BotPos
from backend.llms.data import get_llms_data
from backend.llms.models import LLMData
from backend.llms.utils import Consumption, get_llm_consumption
from utils.database.models import ComparisonRead

logger = logging.getLogger("languia")


class RevealModelData(TypedDict):
    llm: LLMData
    conso: Consumption


class RevealData(TypedDict):
    b64: str
    chosen_llm: BotPos | None
    a: RevealModelData
    b: RevealModelData


def get_chosen_llm(comparison: ComparisonRead) -> BotPos | None:
    """
    Compute the better LLM based on turn votes.

    Args:
        comparison: ComparisonRead

    Returns:
        BotPos | None: the computed LLM pos or None if it is a draw.
    """
    scores: dict[BotPos, int] = {"a": 0, "b": 0}
    for turn in comparison.turns:
        if turn.choice == "a_better":
            scores["a"] += 1
        elif turn.choice == "b_better":
            scores["b"] += 1

    if scores["a"] > scores["b"]:
        return "a"
    if scores["b"] > scores["a"]:
        return "b"

    return None


def get_reveal_data(comparison: ComparisonRead) -> RevealData:
    """
    Build reveal screen data with LLM comparison and environmental impact metrics.

    Calculates environmental impact (energy, CO2 emissions) and creates data for the
    reveal screen shown after voting. Includes LLM definitions, token counts, and
    scaled equivalence (e.g., "if all the population made this prompt…").

    Args:
        comparison: ComparisonRead
        chosen_llm: Computed better LLM pos or None if equal based on votes

    Returns:
        dict: RevealData containing:
            - b64: Base64-encoded JSON summary (compact storage/transmission)
            - chosen_llm: Computed better LLM pos ("a", "b" or None)
            - a: llm 'a' definition (see `LLMData`) and conso (see `Consumption`)
            - b: llm 'b' definition (see `LLMData`) and conso (see `Consumption`)

    Process:
        1. Compute total output tokens for each LLM turns
        2. Compute `Consumption` data for each LLM turns
        3. Encode summary to base64 for efficient storage
        4. Return comprehensive metrics for reveal screen display
    """
    import base64
    import json

    # TODO: Add request_latency for more accurate impact calculations
    # Currently not tracked; would need start/finish timestamps from Conversation
    # Compute it for each exchange (user prompt/llm response)
    # request_latency = conv.finish_tstamp - conv.start_tstamp

    chosen_llm = get_chosen_llm(comparison)
    llms = get_llms_data(comparison.country_portal).enabled
    # Calculate environmental impact using ecologits library
    # Uses llm params, active params (for MoE) and token count
    conso: dict[BotPos, Consumption] = {
        "a": get_llm_consumption(
            llms[comparison.llm_id_a],
            sum(turn.llm_msg_a.tokens for turn in comparison.turns),
        ),
        "b": get_llm_consumption(
            llms[comparison.llm_id_b],
            sum(turn.llm_msg_b.tokens for turn in comparison.turns),
        ),
    }

    logger.debug(f"[REVEAL] output_tokens (llm 'a'): {conso["a"]["tokens"]}")
    logger.debug(f"[REVEAL] output_tokens (llm 'b'): {conso["b"]["tokens"]}")

    # Encode summary as base64 for safe storage/transmission (share feature)
    jsonstring = json.dumps(
        {
            "a": comparison.llm_id_a,  # Model A identifier
            "b": comparison.llm_id_b,  # Model B identifier
            "ta": conso["a"]["tokens"],  # Model A token count
            "tb": conso["b"]["tokens"],  # Model B token count
            # Add user's choice to summary (for verification/tracking)
            "c": chosen_llm,
        }
    ).encode("ascii")
    b64 = base64.b64encode(jsonstring).decode("ascii")

    # Return comprehensive reveal data for frontend display
    return {
        "b64": b64,
        "chosen_llm": chosen_llm,
        "a": {"llm": llms[comparison.llm_id_a], "conso": conso["a"]},
        "b": {"llm": llms[comparison.llm_id_b], "conso": conso["b"]},
    }
