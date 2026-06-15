"""
Script computing ranking/preferences and stores results in redis or as json file.
Ran at interval by a cronjob.
"""

import json
import logging
from pathlib import Path
from typing import Literal

import cyclopts
from fastapi.encoders import jsonable_encoder

from backend.config import settings
from utils.storage.redis import REDIS_RANKING_KEY, get_redis_client
from utils.utils import (
    LLMS_GENERATED_DATA_FILE,
    configure_logger,
    read_json,
    write_json,
)

from .compute import RankingResult, compute_ranking
from .monitor import monitor

logger = configure_logger(logging.getLogger("ranking.run"))

LLMS_RANKING_DATA_FILE = Path(__file__).parent / "generated-ranking-all.json"


def store_to_redis(data: RankingResult) -> None:
    """
    Stores `RankingResult` in redis cache for this instance's portal.

    Note:
        Expires after 24 hours but should be recomputed at interval with a cronjob.
    """
    try:
        client = get_redis_client()
        client.setex(
            REDIS_RANKING_KEY,
            time=3600 * 24,
            value=json.dumps(data),
        )
        logger.info(
            f"[SESSION] Stored ranking data for {settings.DEFAULT_LOCALE}"
        )
    except Exception as e:
        logger.error(f"[SESSION] Error storing ranking data: {e}")
        raise


async def main(*, mode: Literal["all", "redis", "json"] = "redis") -> None:
    """
    Compute rankings and store results in redis or as file depending on mode.
    """
    ranking = await compute_ranking()

    if not ranking:
        return

    if mode in ("all", "json"):
        # FIXME reflect previous data structure and override utils/models/generated-models-extra-data.json?
        write_json(LLMS_RANKING_DATA_FILE, jsonable_encoder(ranking))

    if mode in ("all", "redis"):
        store_to_redis(jsonable_encoder(ranking))

    llms = read_json(LLMS_GENERATED_DATA_FILE)["models"]
    await monitor(llms, ranking)


if __name__ == "__main__":
    cyclopts.run(main)
