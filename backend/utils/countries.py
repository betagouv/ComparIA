import logging
from typing import Annotated, cast

from pydantic import BeforeValidator

from backend.config import (
    COUNTRY_PORTALS,
    DEFAULT_COUNTRY_PORTAL,
    CountryPortal,
    settings,
)

logger = logging.getLogger("languia")


def get_country_portal(code: str | None = DEFAULT_COUNTRY_PORTAL) -> CountryPortal:
    return (
        DEFAULT_COUNTRY_PORTAL
        if code not in COUNTRY_PORTALS
        else cast(CountryPortal, code)
    )


CountryPortalAnno = Annotated[CountryPortal, BeforeValidator(get_country_portal)]


def get_country_portal_count(country_code: CountryPortal, ttl: int = 120) -> int:
    """
    Get the count of votes and reactions for conversations with a specific country portal.

    Args:
        country_code: The country code to filter by (e.g., 'da' for Danish)
        ttl: Time-to-live for Redis cache in seconds (default: 120 seconds = 2 minutes)

    Returns:
        The count of votes and reactions for the specified country portal
    """
    import psycopg2
    from psycopg2 import sql

    from backend.session import r

    cache_key = f"{country_code}_count"
    # Try Redis first
    if r:
        try:
            count = r.get(cache_key)
            if count is not None:
                return int(count)
        except Exception as e:
            logger.debug(f"cache miss for {country_code} count from Redis: {e}")

    # Fallback to Postgres
    if not settings.COMPARIA_DB_URI:
        logger.warning("Cannot log to db: no db configured")
        return 0

    conn = None
    cursor = None
    result = 0
    try:
        conn = psycopg2.connect(settings.COMPARIA_DB_URI)
        cursor = conn.cursor()
        # Count votes and reactions linked to conversations with country_portal
        query = sql.SQL(
            """
            SELECT
                (SELECT COUNT(*) FROM votes v
                 JOIN conversations c ON v.conversation_pair_id = c.conversation_pair_id
                 WHERE c.country_portal = %s) +
                (SELECT COUNT(*) FROM reactions r
                 JOIN conversations c ON r.conversation_pair_id = c.conversation_pair_id
                 WHERE c.country_portal = %s)
            as total;
        """
        )
        cursor.execute(query, (country_code, country_code))
        res = cursor.fetchone()
        result = res[0] if res and res[0] is not None else 0

        if r:
            try:
                r.setex(cache_key, ttl, result)
            except Exception as e:
                logger.error(f"Error setting {country_code} count in Redis: {e}")

        return result
    except Exception as e:
        logger.error(f"Error getting {country_code} count from db: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
