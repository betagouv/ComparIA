import json
import logging
from typing import Awaitable

from sqlmodel import and_, col, func, select

from backend.config import settings
from utils.database.models import Comparison, Turn
from utils.database.session import get_session
from utils.ranking.compute import RankingResult
from utils.storage.redis import (
    REDIS_RANKING_KEY,
    REDIS_VOTE_COUNT_KEY,
    get_redis_client,
)

logger = logging.getLogger("languia")


async def get_vote_count(ttl: int = 120) -> int:
    """
    Get the count of Turns with vote choice from redis if available or compute it.

    Args:
        ttl: Time-to-live for Redis cache in seconds (default: 120 seconds = 2 minutes)

    Returns:
        The count of Turns with vote choice.
    """

    # Try Redis first
    client = get_redis_client()
    try:
        count = client.get(REDIS_VOTE_COUNT_KEY)
        assert not isinstance(count, Awaitable)
        if count is not None:
            return int(count)
    except Exception as e:
        logger.debug(f"cache miss for vote count from Redis: {e}")

    # Fallback to Postgres
    if not settings.COMPARIA_DB_URI:
        logger.warning("Cannot log to db: no db configured")
        return 0

    # Count Turn's with choice
    async with get_session() as session:
        count = (
            await session.exec(
                select(func.count(col(Turn.id)))
                .join(Comparison)
                .where(col(Comparison.archived).is_not(True))
                .where(and_(Turn.choice != None, Turn.choice != "idk"))
            )
        ).one()

        try:
            client.setex(REDIS_VOTE_COUNT_KEY, ttl, count)
        except Exception as e:
            logger.error(f"Error setting vote count in Redis: {e}")

        return count

    return 0


def get_ranking() -> RankingResult | None:
    """
    Get ranking and preference data from redis cache if available.
    """

    data_info = f"ranking and prefs data"

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
