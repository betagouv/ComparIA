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

from utils.storage.redis import REDIS_RANKING_KEY, REDIS_TOOL_RANKING_KEY, get_redis_client
from utils.utils import (
    LLMS_GENERATED_DATA_FILE,
    configure_logger,
    read_json,
    write_json,
)

from .compute import DataGroup, RankingResult, compute_all_rankings
from .monitor import monitor
from .tool_compute import compute_tool_rankings

logger = configure_logger(logging.getLogger("ranking.run"))

LLMS_RANKING_DATA_FILE = Path(__file__).parent / "generated-ranking-all.json"


def store_to_redis(group: DataGroup, data: RankingResult) -> None:
    """
    Stores per group (portals + all) `RankingResult` in redis cache for comparia instances.

    Note:
        Expires after 24 hours but should be recomputed at interval with a cronjob.
    """
    data_info = f"ranking and prefs data for group: {group}"

    try:
        client = get_redis_client()
        client.setex(
            REDIS_RANKING_KEY.format(country_portal=group),
            time=3600 * 24,
            value=json.dumps(data),
        )
        logger.info(f"[SESSION] Stored {data_info}")
    except Exception as e:
        logger.error(f"[SESSION] Error storing {data_info}: {e}")
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
        for k in data.keys():
            store_to_redis(k, jsonable_encoder(data[k]))

    llms = read_json(LLMS_GENERATED_DATA_FILE)["models"]
    monitor(llms, data["all"])

    compute_and_store_tool_rankings()


def compute_and_store_tool_rankings() -> None:
    """Compute tool rankings and store to Redis under REDIS_TOOL_RANKING_KEY."""
    try:
        result = compute_tool_rankings()
        if result is None:
            return
        client = get_redis_client()
        client.setex(
            REDIS_TOOL_RANKING_KEY,
            time=3600 * 24,
            value=json.dumps(jsonable_encoder(result)),
        )
        logger.info("[ToolRanking] Stored tool rankings to Redis")
    except Exception as e:
        logger.error(f"[ToolRanking] Error storing tool rankings: {e}")


if __name__ == "__main__":
    cyclopts.run(main)
