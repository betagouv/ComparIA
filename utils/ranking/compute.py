"""
Ranking computation orchestration.

Fetches votes/reactions from DB, groups by country portal,
runs Bradley-Terry, and returns results matching the DatasetData
and PreferencesData shapes from backend/llms/models.py.
"""

import logging
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal

from backend.config import ALL_PREFS, NEGATIVE_PREFS, POSITIVE_PREFS, CountryPortal
from backend.llms.models import DatasetData, PreferencesData
from utils.ranking.bradley_terry import bootstrap_confidence_intervals
from utils.ranking.queries import fetch_votes
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.compute"))

DataGroup = Literal[CountryPortal, "all"]


@dataclass
class RankingResult:
    timestamp: float
    rankings: dict[str, DatasetData] = field(default_factory=dict)
    preferences: dict[str, PreferencesData] = field(default_factory=dict)


def _votes_to_battles(votes: list[dict]) -> list[tuple[str, str, str]]:
    """Convert vote records to battle tuples, filtering ties."""
    battles = []
    for v in votes:
        if v["choice"] in ("a_better", "b_better"):
            winner = v["llm_id_a"] if v["choice"] == "a_better" else v["llm_id_b"]
            battles.append((v["llm_id_a"], v["llm_id_b"], winner))

    return battles


def _aggregate_preferences(votes: list[dict]) -> dict[str, PreferencesData]:
    """Aggregate preference booleans from votes per model."""
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {f: 0 for f in ALL_PREFS})
    total: dict[str, int] = defaultdict(int)

    for v in votes:
        for side in ("a", "b"):
            model = v[f"llm_id_{side}"]
            total[model] += 1
            for keyword in v[f"keyword_annotations_{side}"]:
                counts[model][keyword] += 1

    result = {}
    for model in total:
        c = counts[model]
        positive_count = sum(c[f] for f in POSITIVE_PREFS)
        negative_count = sum(c[f] for f in NEGATIVE_PREFS)
        all_prefs_count = positive_count + negative_count

        result[model] = PreferencesData(
            positive_prefs_ratio=(
                positive_count / all_prefs_count if all_prefs_count > 0 else -1
            ),
            total_prefs=total[model],
            useful=c["useful"],
            complete=c["complete"],
            creative=c["creative"],
            clear_formatting=c["clear_formatting"],
            incorrect=c["incorrect"],
            superficial=c["superficial"],
            instructions_not_followed=c["instructions_not_followed"],
        )

    return result


def _compute_rankings_for_group(
    votes: list[dict],
) -> RankingResult:
    """Compute rankings and preferences for a single group of votes/reactions."""
    all_battles = _votes_to_battles(votes)

    if not all_battles:
        return RankingResult(timestamp=time.time())

    # (point_estimate, lower_2.5, upper_97.5) per model
    ci = bootstrap_confidence_intervals(all_battles)

    # Count matches and wins per model
    match_counts: dict[str, int] = defaultdict(int)
    win_counts: dict[str, int] = defaultdict(int)
    for a, b, winner in all_battles:
        match_counts[a] += 1
        match_counts[b] += 1
        win_counts[winner] += 1

    # Drop degenerate models (never won or never lost in the full data)
    ci = {m: v for m, v in ci.items() if not any(math.isnan(x) for x in v)}

    # Sort by point-estimate Elo descending
    sorted_models = sorted(ci, key=lambda m: -ci[m][0])
    n_total = len(sorted_models)

    rankings: dict[str, DatasetData] = {}
    for rank, model in enumerate(sorted_models, 1):
        elo_point, elo_lower, elo_upper = ci[model]
        n_match = match_counts.get(model, 0)
        wins = win_counts.get(model, 0)

        # Rank bounds via CI overlap:
        # rank_best = 1 + models whose lower CI > this model's upper CI
        # rank_worst = N - models whose upper CI < this model's lower CI
        rank_best = 1
        rank_worst = n_total
        for other in sorted_models:
            if other == model:
                continue
            if ci[other][1] > elo_upper:
                rank_best += 1
            if elo_lower > ci[other][2]:
                rank_worst -= 1

        # Mean win probability: P(i beats j) = s_i / (s_i + s_j), averaged
        strength_i = 10 ** ((elo_point - 1000) / 400)
        win_probs = []
        for other in sorted_models:
            if other == model:
                continue
            strength_j = 10 ** ((ci[other][0] - 1000) / 400)
            win_probs.append(strength_i / (strength_i + strength_j))
        mean_win_prob = sum(win_probs) / len(win_probs) if win_probs else 0.5

        rankings[model] = DatasetData(
            elo=round(elo_point),
            score_p2_5=round(elo_lower),
            score_p97_5=round(elo_upper),
            rank=rank,
            rank_p2_5=rank_best,
            rank_p97_5=rank_worst,
            n_match=n_match,
            mean_win_prob=round(mean_win_prob, 4),
            win_rate=round(wins / n_match, 4) if n_match > 0 else 0.0,
        )

    preferences = _aggregate_preferences(votes)

    return RankingResult(
        timestamp=time.time(),
        rankings=rankings,
        preferences=preferences,
    )


async def compute_all_rankings() -> dict[DataGroup, RankingResult]:
    """
    Main function called by the scheduler.

    Fetches all votes and reactions (one query each), groups by country_portal,
    computes rankings for each portal + an "all" global group.

    Returns:
        Dict mapping portal code (or "all") to RankingResult.
    """
    logger.info("[Ranking] Starting ranking computation...")
    start = time.time()

    all_votes = await fetch_votes()
    print(all_votes)

    if not all_votes:
        logger.warning("[Ranking] No votes or reactions found, skipping computation")
        return {}

    # Group by country_portal
    votes_by_portal: dict[str, list[dict]] = defaultdict(list)

    for v in all_votes:
        portal = v.get("country_portal", "unknown")
        votes_by_portal[portal].append(v)

    # Get all portal keys (excluding unknown)
    all_portals = set(votes_by_portal.keys())
    all_portals.discard("unknown")

    results: dict[DataGroup, RankingResult] = {}

    for portal in all_portals:
        try:
            results[portal] = _compute_rankings_for_group(
                votes_by_portal.get(portal, []),
            )
        except Exception:
            logger.error(
                f"[Ranking] Error computing rankings for portal {portal}",
                exc_info=True,
            )

    # Global rankings using all votes/reactions
    try:
        results["all"] = _compute_rankings_for_group(all_votes)
    except Exception:
        logger.error("[Ranking] Error computing global rankings", exc_info=True)

    elapsed = time.time() - start
    portals = list(results.keys())
    logger.info(f"[Ranking] Updated rankings for portals: {portals} in {elapsed:.1f}s")

    return results
