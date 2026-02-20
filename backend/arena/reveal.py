"""
Reveal screen data generation.

Functions:
- get_chosen_llm: Guess the chosen LLM
- get_equivalence_seed: Generate deterministic seed from conversation IDs
- get_reveal_data: Main function generating reveal screen data
"""

import logging

from backend.arena.models import BotChoice, BotPos, Conversations, RevealData
from backend.llms.utils import get_all_meaningful_equivalences, get_llm_consumption

logger = logging.getLogger("languia")


def get_chosen_llm(conversations: Conversations) -> BotChoice | None:
    """
    Guess the chosen LLM based on vote or reaction data.

    Args:
        conversations: Conversations

    Returns:
        BotChoice | None: the computed choice or None if no vote or reactions is found
    """
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


def get_reveal_data(conversations: Conversations, chosen_llm: BotChoice) -> RevealData:
    """
    Build reveal screen data with model comparison and environmental impact metrics.

    Calculates environmental impact (energy, CO2 emissions) and creates data for the
    reveal screen shown after voting. Includes model metadata, token counts, and
    scaled equivalence (e.g., "if 1 billion people used this daily for a year").

    Args:
        conversations: Conversation object for model B with messages, model_name, and conv_id
        chosen_llm: User's choice ("a", "b", or "both_equal")

    Returns:
        dict: RevealData containing:
            - b64: Base64-encoded JSON summary (compact storage/transmission)
            - chosen_llm: User's model preference ("a", "b" or None)
            - a: llm 'a' data (see `LLMData`) and conso (see `Consumption`)
            - b: llm 'b' data (see `LLMData`) and conso (see `Consumption`)
            - equivalences: all meaningful scaled consumptions equivalences

    Process:
        1. Compute total output tokens for each conversation
        2. Compute `Consumption` data for each conversation
        3. Select random equivalence type (seeded by conversation IDs for consistency)
        4. Calculate scaled equivalence values for both models
        5. Encode summary to base64 for efficient storage
        6. Return comprehensive metrics for reveal screen display
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

    # Get all meaningful equivalences for both models
    # Uses conversation IDs as seed for consistent shuffling across page refreshes
    seed = get_equivalence_seed(conv_a.conv_id, conv_b.conv_id)
    equivalences = get_all_meaningful_equivalences(conso_a, conso_b, seed)

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
        # All meaningful scaled equivalences (frontend can cycle through them)
        # Each contains: type, model_a_value, model_b_value
        "equivalences": equivalences,
    }
