"""
Ranking cache and async scheduler.

Provides:
- Module-level cache of computed rankings keyed by portal code
- Async scheduler that periodically recomputes rankings in a background thread
- Thread-safe reads (single-writer via asyncio, readers get a consistent dict reference)
"""

import asyncio
import logging

from backend.ranking.compute import RankingResult, compute_all_rankings

logger = logging.getLogger("languia")

# Module-level cache: portal code -> RankingResult
_ranking_cache: dict[str, RankingResult] = {}


def get_cached_rankings(portal: str) -> RankingResult | None:
    """Read cached rankings for a portal. Returns None if not yet computed."""
    return _ranking_cache.get(portal)


async def ranking_scheduler(interval_seconds: int) -> None:
    """
    Async loop that periodically computes rankings and updates the cache.

    Runs compute_all_rankings() in a thread (via asyncio.to_thread) to avoid
    blocking the event loop. First computation runs immediately (no initial sleep).

    Logs exceptions but never crashes — stale cache is better than no cache.
    """
    logger.info(
        f"[Ranking] Scheduler started (interval={interval_seconds}s)"
    )

    while True:
        try:
            results = await asyncio.to_thread(compute_all_rankings)
            if results:
                _ranking_cache.update(results)
        except asyncio.CancelledError:
            logger.info("[Ranking] Scheduler cancelled")
            return
        except Exception:
            logger.error("[Ranking] Scheduler error", exc_info=True)

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("[Ranking] Scheduler cancelled during sleep")
            return
