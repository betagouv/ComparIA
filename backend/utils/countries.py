import json
import logging
from typing import Annotated, Awaitable, cast

from fastapi import Depends, Header, HTTPException, status

from backend.config import (
    COUNTRY_PORTALS,
    DEFAULT_COUNTRY_PORTAL,
    CountryPortal,
    settings,
)
from utils.ranking.compute import RankingResult
from utils.storage.db import db_cursor
from utils.storage.queries import get_reactions_db_query, get_votes_db_query
from utils.storage.redis import (
    REDIS_RANKING_KEY,
    REDIS_VOTE_COUNT_KEY,
    get_redis_client,
)

logger = logging.getLogger("languia")


def country_portal_from_locale(locale: str = Header(..., alias="X-Locale")) -> str:
    """
    Dependency to extract and validate country portal from headers's locale.

    Args:
        locale: Session identifier from X-Locale header

    Returns:
        CountryPortal

    Raises:
        HTTPException: If locale is missing
    """
    if not locale:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing locale in headers"
        )

    return (
        DEFAULT_COUNTRY_PORTAL
        if locale not in COUNTRY_PORTALS
        else cast(CountryPortal, locale)
    )


CountryPortalAnno = Annotated[CountryPortal, Depends(country_portal_from_locale)]


def get_country_portal_count(country_code: CountryPortal, ttl: int = 1200) -> int:
    """
    Get the count of votes and reactions for conversations with a specific country portal.

    Args:
        country_code: The country code to filter by (e.g., 'da' for Danish)
        ttl: Time-to-live for Redis cache in seconds (default: 120 seconds = 2 minutes)

    Returns:
        The count of votes and reactions for the specified country portal
    """
    from psycopg2 import sql

    cache_key = REDIS_VOTE_COUNT_KEY.format(country_code=country_code)
    # Try Redis first
    client = get_redis_client()
    try:
        count = client.get(cache_key)
        assert not isinstance(count, Awaitable)
        if count is not None:
            return int(count)
    except Exception as e:
        logger.debug(f"cache miss for {country_code} count from Redis: {e}")

    # Fallback to Postgres
    if not settings.COMPARIA_DB_URI:
        logger.warning("Cannot log to db: no db configured")
        return 0

    # Count votes and reactions linked to conversations with country_portal
    with db_cursor("get votes and reactions count", logger) as cursor:
        votes_query = get_votes_db_query(
            country_portal=country_code, count=True, exclude_pii=False
        )
        reactions_query = get_reactions_db_query(
            country_portal=country_code, count=True, exclude_pii=False
        )
        cursor.execute(
            sql.SQL(f"SELECT ({votes_query}) + ({reactions_query}) as total;")
        )
        # FIXME raise error if None?
        res = cursor.fetchone()
        result = res[0] if res and res[0] is not None else 0

        try:
            client.setex(cache_key, ttl, result)
        except Exception as e:
            logger.error(f"Error setting {country_code} count in Redis: {e}")

        return result

    return 0


def get_country_portal_ranking(country_portal: CountryPortal) -> RankingResult | None:
    """
    Get ranking and preference data for a specific portal from redis cache.

    Args:
        country_portal: The country portal to filter by (e.g., 'da' for Danish)
    """

    data_info = f"ranking and prefs data for country_portal: {country_portal}"

    try:
        client = get_redis_client()
        data = client.get(REDIS_RANKING_KEY.format(country_portal=country_portal))
        assert not isinstance(data, Awaitable)

        if data is None:
            logger.error(f"[REDIS] No cached {data_info}")
            return None

        logger.info(f"[REDIS] Retrieved {data_info}")
        return RankingResult(**json.loads(data))
    except json.JSONDecodeError as e:
        logger.error(f"[REDIS] Error decoding {data_info}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"[REDIS] Error retrieving {data_info}: {e}", exc_info=True)
        return None
