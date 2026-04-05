"""
Tool ranking computation using Bradley-Terry model.

Isolated from the LLM ranking path (compute.py) per D-01.
Only shared primitive: bootstrap_confidence_intervals from bradley_terry.py.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

from utils.ranking.bradley_terry import bootstrap_confidence_intervals
from utils.ranking.tool_queries import fetch_tool_votes
from utils.utils import configure_logger

logger = configure_logger(logging.getLogger("ranking.tool_compute"))

PROVISIONAL_THRESHOLD = 50


@dataclass
class ToolRankingEntry:
    tool_id: str
    elo: int
    score_p2_5: int
    score_p97_5: int
    n_match: int
    win_rate: float
    provisional: bool


@dataclass
class ToolRankingResult:
    timestamp: float
    rankings: dict[str, ToolRankingEntry] = field(default_factory=dict)


def _tool_votes_to_battles(votes: list[dict]) -> list[tuple[str, str, str]]:
    """Convert tool vote records to battle tuples, filtering ties."""
    battles = []
    for v in votes:
        if v["chosen"] == "tie":
            continue
        winner = v["tool_a_id"] if v["chosen"] == "a" else v["tool_b_id"]
        battles.append((v["tool_a_id"], v["tool_b_id"], winner))
    return battles


def compute_tool_rankings() -> ToolRankingResult | None:
    """
    Main function for tool ranking computation.

    Fetches votes from DB, converts to battles, runs Bradley-Terry with
    bootstrap confidence intervals, and returns ToolRankingResult.

    Returns:
        ToolRankingResult with empty rankings dict if no battles exist.
        None only on unexpected failure.
    """
    try:
        votes = fetch_tool_votes()
    except Exception:
        logger.error("[ToolRanking] Failed to fetch tool votes", exc_info=True)
        return None

    battles = _tool_votes_to_battles(votes)

    if not battles:
        logger.warning("[ToolRanking] No tool battles found, returning empty result")
        return ToolRankingResult(timestamp=time.time())

    ci = bootstrap_confidence_intervals(battles, n_samples=100)

    match_counts: dict[str, int] = defaultdict(int)
    win_counts: dict[str, int] = defaultdict(int)
    for a, b, winner in battles:
        match_counts[a] += 1
        match_counts[b] += 1
        win_counts[winner] += 1

    rankings: dict[str, ToolRankingEntry] = {}
    for tool_id, (elo_median, elo_lower, elo_upper) in ci.items():
        n_match = match_counts.get(tool_id, 0)
        wins = win_counts.get(tool_id, 0)
        rankings[tool_id] = ToolRankingEntry(
            tool_id=tool_id,
            elo=round(elo_median),
            score_p2_5=round(elo_lower),
            score_p97_5=round(elo_upper),
            n_match=n_match,
            win_rate=round(wins / n_match, 4) if n_match > 0 else 0.0,
            provisional=n_match < PROVISIONAL_THRESHOLD,
        )

    return ToolRankingResult(timestamp=time.time(), rankings=rankings)
