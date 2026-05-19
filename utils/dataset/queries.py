import logging

from utils.storage.queries import get_conversations_db_query, get_votes_db_query

from .models import Datasets

logger = logging.getLogger("comparia.dataset")


def get_dataset_queries() -> dict[Datasets, str]:
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
            )
        ),
        "votes": get_votes_db_query(
            columns={
                "v": ("*",),
                "c": (
                    "visitor_id",
                    "ip",
                    "conv_turns",
                    "model_pair_name",
                    "opening_msg",
                    "model_a_name",
                    "model_b_name",
                    "system_prompt_a",
                    "system_prompt_b",
                    "conversation_a",
                    "conversation_b",
                ),
            }
        ),
        "reactions": get_reactions_db_query(
            columns={
                "r": (
                    "id",
                    "timestamp",
                    "session_hash",
                    "conversation_pair_id",
                    "current_conv_turn_when_reacting",
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
                "c": (
                    "visitor_id",
                    "conv_turns",
                    "model_pair_name",
                    "opening_msg",
                    "model_a_name",
                    "model_b_name",
                    "conv_a_id",
                    "conv_b_id",
                    "conversation_a",
                    "conversation_b",
                ),
            }
        ),
        # FIXME this exclude compromised data but was not
        "conversations_raw": get_conversations_db_query(
            columns="*",
            exclude_pii=False,
            exclude_cohorts=False,
        ),
    }
