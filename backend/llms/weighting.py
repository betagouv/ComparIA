"""
Weighted sampling for model selection.

Biases random model picking toward models with fewer recorded battles so
vote counts converge across the catalog. Consumes per-model `n_match`
already computed by the ranking pipeline (utils/ranking/compute.py) and
cached in Redis under `rankings_and_prefs:{country_portal}`, so selection
never hits the DB.

Weight per model:
    w_i = 1 / (n_match_i + smoothing) ** alpha

then normalized and clipped so max/min weight ratio <= max_ratio.

alpha = 0 gives uniform sampling. alpha ~ 0.4 gives a mild catch-up
bias while keeping the sampling distribution close enough to uniform
that Bradley-Terry / Elo computations downstream remain trustworthy.
"""

import numpy as np

from backend.config import settings
from utils.ranking.compute import RankingResult


def compute_weights(
    models_pool: list[str],
    ranking: RankingResult | None,
) -> np.ndarray | None:
    """
    Normalized sampling weights for `models_pool`, or None when
    weighting is disabled / ranking data is unavailable (caller falls
    back to uniform sampling).
    """
    if not settings.WEIGHTED_SAMPLING_ENABLED:
        return None

    if len(models_pool) <= 1 or ranking is None or not ranking.rankings:
        return None

    alpha = settings.WEIGHTED_SAMPLING_ALPHA
    smoothing = settings.WEIGHTED_SAMPLING_SMOOTHING
    max_ratio = settings.WEIGHTED_SAMPLING_MAX_RATIO

    counts = np.array(
        [
            ranking.rankings[m].n_match if m in ranking.rankings else 0
            for m in models_pool
        ],
        dtype=np.float64,
    )

    weights = 1.0 / np.power(counts + smoothing, alpha)

    if max_ratio > 1.0:
        w_min = weights.min()
        weights = np.minimum(weights, w_min * max_ratio)

    total = weights.sum()
    if total <= 0 or not np.isfinite(total):
        return None

    return weights / total
