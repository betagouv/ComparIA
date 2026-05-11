import json
import logging
from typing import Annotated, Awaitable, cast

from fastapi import Depends, Header, HTTPException, status
from sqlmodel import and_, col, func, select

from backend.config import (
    COUNTRY_PORTALS,
    DEFAULT_COUNTRY_PORTAL,
    CountryPortal,
    settings,
)
from utils.database.models import Comparison, Turn
from utils.database.session import get_session
from utils.ranking.compute import RankingResult
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


async def get_country_portal_count(country_code: CountryPortal, ttl: int = 120) -> int:
    """
    Get the count of votes and reactions for conversations with a specific country portal.

    Args:
        country_code: The country code to filter by (e.g., 'da' for Danish)
        ttl: Time-to-live for Redis cache in seconds (default: 120 seconds = 2 minutes)

    Returns:
        The count of votes and reactions for the specified country portal
    """

    # Try Redis first
    client = get_redis_client()
    try:
        count = client.get(REDIS_VOTE_COUNT_KEY)
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
    async with get_session() as session:
        count = (
            await session.exec(
                select(func.count(col(Turn.id)))
                .join(Comparison)
                .where(col(Comparison.archived).is_not(True))
                .where(Comparison.country_portal == country_code)
                .where(and_(Turn.choice != None, Turn.choice != "idk"))
            )
        ).one()

        try:
            client.setex(REDIS_VOTE_COUNT_KEY, ttl, count)
        except Exception as e:
            logger.error(f"Error setting {country_code} count in Redis: {e}")

        return count

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
        data = client.get(REDIS_RANKING_KEY)
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
