"""
Database queries for fetching vote and reaction data for ranking computation.

Uses psycopg2 with RealDictCursor, matching the existing pattern
from backend/arena/persistence.py and backend/utils/countries.py.
"""

import logging

import psycopg2
from psycopg2.extras import RealDictCursor

from backend.config import settings

logger = logging.getLogger("languia")


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
    if not settings.COMPARIA_DB_URI:
        return []

    query = """
        SELECT
            v.model_a_name,
            v.model_b_name,
            v.chosen_model_name,
            v.both_equal,
            v.conv_useful_a,
            v.conv_useful_b,
            v.conv_complete_a,
            v.conv_complete_b,
            v.conv_creative_a,
            v.conv_creative_b,
            v.conv_clear_formatting_a,
            v.conv_clear_formatting_b,
            v.conv_incorrect_a,
            v.conv_incorrect_b,
            v.conv_superficial_a,
            v.conv_superficial_b,
            v.conv_instructions_not_followed_a,
            v.conv_instructions_not_followed_b,
            c.country_portal
        FROM votes v
        JOIN conversations c ON v.conversation_pair_id = c.conversation_pair_id
        WHERE v.archived IS NOT TRUE
          AND c.archived IS NOT TRUE
    """
    conn = None
    try:
        conn = psycopg2.connect(settings.COMPARIA_DB_URI)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error as e:
        logger.error(f"[Ranking] Error fetching votes: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()


def fetch_reactions() -> list[dict]:
    """
    Fetch all non-archived reactions joined with conversations for country_portal.

    Returns:
        List of dicts with keys: model_a_name, model_b_name, refers_to_model,
        liked, disliked, country_portal.
    """
    if not settings.COMPARIA_DB_URI:
        return []

    query = """
        SELECT
            r.model_a_name,
            r.model_b_name,
            r.refers_to_model,
            r.liked,
            r.disliked,
            c.country_portal
        FROM reactions r
        JOIN conversations c ON r.conversation_pair_id = c.conversation_pair_id
        WHERE r.archived IS NOT TRUE
          AND c.archived IS NOT TRUE
    """
    conn = None
    try:
        conn = psycopg2.connect(settings.COMPARIA_DB_URI)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except psycopg2.Error as e:
        logger.error(f"[Ranking] Error fetching reactions: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()
