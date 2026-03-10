import json
import logging
from functools import lru_cache
from typing import Literal

from backend.config import CountryPortal
from backend.llms.models import LLMData
from utils.storage.queries import (
    get_conversations_db_query,
    get_reactions_db_query,
    get_votes_db_query,
)
from utils.utils import LLMS_GENERATED_DATA_FILE, read_json

logger = logging.getLogger("dataset")

Datasets = Literal["conversations", "votes", "reactions", "conversations_raw"]


@lru_cache
def get_llms_data() -> dict[str, LLMData]:
    """
    Load the generated models JSON data.
    Used to enrich conversations with model metadata (params count, energy consumption).
    """
    try:
        llms_data = read_json(LLMS_GENERATED_DATA_FILE)
        return {
            k: LLMData.model_validate(v)
            for k, v in llms_data["models"].items()
            if v.get("status") in ("enabled", "archived")
        }
    except FileNotFoundError:
        logger.error(f"Models JSON file not found at: {LLMS_GENERATED_DATA_FILE}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from: {LLMS_GENERATED_DATA_FILE}")
        raise


def get_dataset_queries(
    country_portal: CountryPortal | None = None,
) -> dict[Datasets, str]:
    """
    Get dataset queries - filter out PII, archived data, and specific cohorts
    All queries exclude: archived=TRUE, contains_pii=TRUE, cohorts matching 'pix' or 'do-not-track'
    """
    return {
        "conversations": get_conversations_db_query(
            columns=(
                "id",
                "timestamp",
                "session_hash",
                "visitor_id",
                "ip",
                "mode",
                "custom_models_selection",
                "conv_turns",
                "conversation_pair_id",
                "model_pair_name",
                "opening_msg",
                "model_a_name",
                "model_b_name",
                "conv_a_id",
                "conv_b_id",
                "system_prompt_a",
                "system_prompt_b",
                "conversation_a",
                "conversation_b",
                "total_conv_a_output_tokens",
                "total_conv_b_output_tokens",
                "short_summary",
                "keywords",
                "categories",
                "languages",
            ),
            country_portal=country_portal,
        ),
        "votes": get_votes_db_query(columns="*", country_portal=country_portal),
        "reactions": get_reactions_db_query(
            columns=(
                "id",
                "timestamp",
                "session_hash",
                "visitor_id",
                "conv_turns",
                "conversation_pair_id",
                "model_pair_name",
                "opening_msg",
                "model_a_name",
                "model_b_name",
                "conv_a_id",
                "conv_b_id",
                "conversation_a",
                "conversation_b",
                "model_pos",
                "refers_to_model",
                "refers_to_conv_id",
                "system_prompt",
                "response_content",
                "question_content",
                "msg_index",
                "msg_rank",
                "question_id",
                "liked",
                "disliked",
                "comment",
                "useful",
                "complete",
                "creative",
                "clear_formatting",
                "incorrect",
                "superficial",
                "instructions_not_followed",
            ),
            country_portal=country_portal,
        ),
        # FIXME this exclude compromised data but was not
        "conversations_raw": get_conversations_db_query(
            columns="*",
            country_portal=country_portal,
            exclude_pii=False,
            exclude_cohorts=False,
        ),
    }
