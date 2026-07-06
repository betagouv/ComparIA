"""
Reveal screen data generation.

Functions:
- get_chosen_llm: Compute the chosen LLM
- get_reveal_data: Main function generating reveal screen data
"""

import logging
from typing import TYPE_CHECKING, TypedDict
from uuid import UUID

from litellm.litellm_core_utils.token_counter import token_counter

from backend.llms.utils import Consumption, get_llm_consumption
from utils.database.models.utils import BotPos

if TYPE_CHECKING:
    from backend.llms.data import LLMsData
    from utils.database.models import ComparisonRead, TurnRead

logger = logging.getLogger("languia")


class RevealModelData(TypedDict):
    llm_id: UUID
    conso: Consumption


class RevealData(TypedDict):
    b64: str
    chosen_llm: BotPos | None
    a: RevealModelData
    b: RevealModelData


def count_input_tokens(
    comparison: "ComparisonRead", pos: BotPos, turns: list["TurnRead"], model: str
) -> int:
    """
    Estimate input tokens sent to the model across the revealed conversation.
    Each generation receives the current user message and the previous messages
    for that model side, so previous turns are counted again when they are resent.
    """
    input_tokens = 0
    history: list[str | None] = []

    if system_msg := getattr(comparison, f"system_msg_{pos}"):
        history.append(system_msg)

    for turn in turns:
        current_messages = [*history, turn.user_msg.content]
        input_tokens += token_counter(
            text=[message for message in current_messages if message],
            model=model,
        )

        history.append(turn.user_msg.content)
        if llm_msg := getattr(turn, f"llm_msg_{pos}"):
            history.extend(
                message
                for message in [llm_msg.reasoning_content, llm_msg.content]
                if message
            )

    return input_tokens


def get_chosen_llm(comparison: "ComparisonRead") -> BotPos | None:
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


def get_reveal_data(comparison: "ComparisonRead", llms: "LLMsData") -> RevealData:
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
    # Calculate environmental impact using ecologits library
    # Uses llm params, active params (for MoE) and token count
    conso: dict[BotPos, Consumption] = {
        "a": get_llm_consumption(
            llms[comparison.llm_id_a],
            sum(turn.llm_msg_a.tokens for turn in comparison.turns),
            count_input_tokens(
                comparison,
                "a",
                comparison.turns,
                str(comparison.llm_id_a),
            ),
        ),
        "b": get_llm_consumption(
            llms[comparison.llm_id_b],
            sum(turn.llm_msg_b.tokens for turn in comparison.turns),
            count_input_tokens(
                comparison,
                "b",
                comparison.turns,
                str(comparison.llm_id_b),
            ),
        ),
    }

    logger.debug(f"[REVEAL] output_tokens (llm 'a'): {conso["a"]["tokens"]}")
    logger.debug(f"[REVEAL] output_tokens (llm 'b'): {conso["b"]["tokens"]}")

    # Encode summary as base64 for safe storage/transmission (share feature)
    jsonstring = json.dumps(
        {
            "a": str(comparison.llm_id_a),  # Model A identifier
            "b": str(comparison.llm_id_b),  # Model B identifier
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
        "a": {"llm_id": comparison.llm_id_a, "conso": conso["a"]},
        "b": {"llm_id": comparison.llm_id_b, "conso": conso["b"]},
    }
