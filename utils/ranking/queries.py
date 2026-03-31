import logging

from psycopg.rows import dict_row

from utils.storage.db import db_cursor
from utils.storage.queries import get_reactions_db_query, get_votes_db_query
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.queries"))


def fetch_votes() -> list[dict]:
    """
    Fetch all non-archived votes joined with conversations for country_portal.

    Returns:
        List of dicts with keys: model_a_name, model_b_name, chosen_model_name,
        both_equal, conv_useful_a, conv_useful_b, conv_complete_a, conv_complete_b,
        conv_creative_a, conv_creative_b, conv_clear_formatting_a, conv_clear_formatting_b,
        conv_incorrect_a, conv_incorrect_b, conv_superficial_a, conv_superficial_b,
        conv_instructions_not_followed_a, conv_instructions_not_followed_b, country_portal.
    """
    with db_cursor("get votes", logger, cursor_factory=dict_row) as cursor:
        cursor.execute(
            get_votes_db_query(
                columns={
                    "v": (
                        "model_a_name",
                        "model_b_name",
                        "chosen_model_name",
                        "both_equal",
                        "conv_useful_a",
                        "conv_useful_b",
                        "conv_complete_a",
                        "conv_complete_b",
                        "conv_creative_a",
                        "conv_creative_b",
                        "conv_clear_formatting_a",
                        "conv_clear_formatting_b",
                        "conv_incorrect_a",
                        "conv_incorrect_b",
                        "conv_superficial_a",
                        "conv_superficial_b",
                        "conv_instructions_not_followed_a",
                        "conv_instructions_not_followed_b",
                    ),
                    "c": ("country_portal",),
                },
                exclude_pii=False,
            )
        )
        return [dict(row) for row in cursor.fetchall()]

    return []


def fetch_reactions() -> list[dict]:
    """
    Fetch all non-archived reactions joined with conversations for country_portal.

    Returns:
        List of dicts with keys: model_a_name, model_b_name, refers_to_model,
        liked, disliked, country_portal.
    """
    with db_cursor("get reactions", logger, cursor_factory=dict_row) as cursor:
        cursor.execute(
            get_reactions_db_query(
                columns={
                    "r": (
                        "model_a_name",
                        "model_b_name",
                        "refers_to_model",
                        "liked",
                        "disliked",
                        "useful",
                        "complete",
                        "creative",
                        "clear_formatting",
                        "incorrect",
                        "superficial",
                        "instructions_not_followed",
                    ),
                    "c": ("country_portal",),
                },
                exclude_pii=False,
            )
        )

        return [dict(row) for row in cursor.fetchall()]

    return []
