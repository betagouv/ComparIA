"""
Bradley-Terry model solver using the MM (minorization-maximization) algorithm.

Computes Elo-like ratings from pairwise comparison data (battles).
Uses vectorized numpy operations for performance.
"""

from uuid import UUID

import numpy as np

Battle = tuple[UUID, UUID, UUID]


def _index_battles(
    battles: list[Battle],
) -> tuple[list[UUID], np.ndarray, np.ndarray, np.ndarray]:
    """Convert string battle tuples to indexed numpy arrays."""
    models = sorted({m for b in battles for m in (b[0], b[1])})
    idx = {m: i for i, m in enumerate(models)}

    ia = np.array([idx[b[0]] for b in battles])
    ib = np.array([idx[b[1]] for b in battles])
    winner_is_a = np.array([b[2] == b[0] for b in battles], dtype=bool)

    return models, ia, ib, winner_is_a


def _fit_from_arrays(
    ia: np.ndarray,
    ib: np.ndarray,
    winner_is_a: np.ndarray,
    n: int,
    max_iter: int = 500,
    tol: float = 1e-6,
) -> np.ndarray:
    """
    Core MM solver on pre-indexed arrays. Returns Elo ratings.

    Models that are absent, undefeated, or winless return NaN, so callers
    (especially the bootstrap) can ignore them rather than treating their
    rating as a wildly negative outlier.

    Wins are constant across iterations so we compute them once.
    Uses np.bincount (histogram) instead of np.add.at (scatter-add) for speed.
    """
    wins = np.bincount(ia, weights=winner_is_a, minlength=n) + np.bincount(
        ib, weights=~winner_is_a, minlength=n
    )
    appearances = np.bincount(ia, minlength=n) + np.bincount(ib, minlength=n)
    # MLE is degenerate (±infinity) for models that never won or never lost,
    # so exclude them from this fit instead of letting the solver clamp them
    # to wild outliers that wreck the bootstrap percentiles.
    present = (appearances > 0) & (wins > 0) & (wins < appearances)

    if not present.any():
        return np.full(n, np.nan)

    p = np.ones(n)
    log_p = np.zeros(n)

    for _ in range(max_iter):
        inv_psum = 1.0 / (p[ia] + p[ib])
        denom = np.bincount(ia, weights=inv_psum, minlength=n) + np.bincount(
            ib, weights=inv_psum, minlength=n
        )

        p = wins / np.maximum(denom, 1e-12)

        # Normalize over present models only so absent ones don't skew the mean
        log_p_new = np.zeros(n)
        log_p_new[present] = np.log(np.maximum(p[present], 1e-12))
        log_p_new[present] -= log_p_new[present].mean()
        p = np.where(present, np.exp(log_p_new), 1.0)

        if np.max(np.abs(log_p_new[present] - log_p[present])) < tol:
            break
        log_p = log_p_new

    elo = 400.0 * np.log10(np.maximum(p, 1e-12)) + 1000.0
    elo[~present] = np.nan
    return elo


def fit_bradley_terry(
    battles: list[Battle],
    max_iter: int = 500,
    tol: float = 1e-6,
) -> dict[UUID, float]:
    """
    Fit a Bradley-Terry model using the MM algorithm.

    Args:
        battles: List of (model_a, model_b, winner) tuples.
            winner must be either model_a or model_b.
        max_iter: Maximum number of iterations.
        tol: Convergence tolerance on log-strength change.

    Returns:
        Dict mapping model name to Elo-like rating centered at 1000.
    """
    if not battles:
        return {}

    models, ia, ib, winner_is_a = _index_battles(battles)
    elo = _fit_from_arrays(ia, ib, winner_is_a, len(models), max_iter, tol)
    return dict(zip(models, elo.tolist()))


def bootstrap_confidence_intervals(
    battles: list[Battle],
    n_samples: int = 500,
) -> dict[UUID, tuple[float, float, float]]:
    """
    Compute Bradley-Terry ratings with bootstrap confidence intervals.

    The displayed Elo is the point estimate from a single fit on the full
    data, not the bootstrap median; the two can drift apart when the
    bootstrap distribution is skewed (e.g. for sparsely-observed models).
    The bootstrap is used only for the CI bounds.

    Bootstrap rounds where a model has no battles, never won, or never lost
    return NaN for that model and are excluded from its percentile, instead
    of being pinned to a huge negative outlier.

    Args:
        battles: List of (model_a, model_b, winner) tuples.
        n_samples: Number of bootstrap samples.

    Returns:
        Dict mapping model name to (point_rating, lower_2.5, upper_97.5).
    """
    if not battles:
        return {}

    models, ia, ib, winner_is_a = _index_battles(battles)
    n_models = len(models)
    n_battles = len(battles)

    point_elo = _fit_from_arrays(ia, ib, winner_is_a, n_models)

    all_elos = np.empty((n_samples, n_models))
    rng = np.random.default_rng()

    for s in range(n_samples):
        idx = rng.integers(0, n_battles, size=n_battles)
        all_elos[s] = _fit_from_arrays(ia[idx], ib[idx], winner_is_a[idx], n_models)

    lowers = np.nanpercentile(all_elos, 2.5, axis=0)
    uppers = np.nanpercentile(all_elos, 97.5, axis=0)

    return {
        models[i]: (float(point_elo[i]), float(lowers[i]), float(uppers[i]))
        for i in range(n_models)
    }
