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

from backend.config import DEFAULT_COUNTRY_PORTAL
from utils.storage.redis import REDIS_RANKING_KEY, get_redis_client
from utils.utils import (
    LLMS_GENERATED_DATA_FILE,
    configure_logger,
    read_json,
    write_json,
)

from .compute import DataGroup, RankingResult, compute_all_rankings
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
        logger.info(f"[SESSION] Stored ranking data for {DEFAULT_COUNTRY_PORTAL}")
    except Exception as e:
        logger.error(f"[SESSION] Error storing ranking data: {e}")
        raise


def main(mode: Literal["all", "redis", "json"] = "redis") -> None:
    """
    Compute per group (portals + "all") `RankingResult` in redis/as file depending on mode.
    """
    data = compute_all_rankings()

    if mode in ("all", "json"):
        # FIXME reflect previous data structure and override utils/models/generated-models-extra-data.json?
        write_json(LLMS_RANKING_DATA_FILE, jsonable_encoder(data["all"]))

    if mode in ("all", "redis"):
        portal_data = data.get(DEFAULT_COUNTRY_PORTAL)
        if portal_data:
            store_to_redis(jsonable_encoder(portal_data))

    llms = read_json(LLMS_GENERATED_DATA_FILE)["models"]
    monitor(llms, data["all"])


if __name__ == "__main__":
    cyclopts.run(main)
