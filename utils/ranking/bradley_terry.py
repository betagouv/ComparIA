"""
Bradley-Terry model solver using the MM (minorization-maximization) algorithm.

Computes Elo-like ratings from pairwise comparison data (battles).
Uses vectorized numpy operations for performance.
"""

import numpy as np


def _index_battles(
    battles: list[tuple[str, str, str]],
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
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

    Wins are constant across iterations so we compute them once.
    Uses np.bincount (histogram) instead of np.add.at (scatter-add) for speed.
    """
    wins = np.bincount(ia, weights=winner_is_a, minlength=n) + np.bincount(
        ib, weights=~winner_is_a, minlength=n
    )

    p = np.ones(n)
    log_p = np.zeros(n)  # log(p), starts at log(1) = 0

    for _ in range(max_iter):
        inv_psum = 1.0 / (p[ia] + p[ib])
        denom = np.bincount(ia, weights=inv_psum, minlength=n) + np.bincount(
            ib, weights=inv_psum, minlength=n
        )

        p = wins / np.maximum(denom, 1e-12)

        # Normalize so geometric mean = 1, and track log(p) for convergence
        log_p_new = np.log(np.maximum(p, 1e-12))
        log_p_new -= log_p_new.mean()
        p = np.exp(log_p_new)

        # Convergence: max change in log-strengths
        if np.max(np.abs(log_p_new - log_p)) < tol:
            break
        log_p = log_p_new

    # Convert to Elo scale: Elo = 400 * log10(p) + 1000
    return 400.0 * np.log10(np.maximum(p, 1e-12)) + 1000.0


def fit_bradley_terry(
    battles: list[tuple[str, str, str]],
    max_iter: int = 500,
    tol: float = 1e-6,
) -> dict[str, float]:
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
    battles: list[tuple[str, str, str]],
    n_samples: int = 100,
) -> dict[str, tuple[float, float, float]]:
    """
    Compute bootstrap confidence intervals for Bradley-Terry ratings.

    Pre-indexes battles once, then resamples index arrays only.

    Args:
        battles: List of (model_a, model_b, winner) tuples.
        n_samples: Number of bootstrap samples.

    Returns:
        Dict mapping model name to (median_rating, lower_2.5, upper_97.5).
    """
    if not battles:
        return {}

    models, ia, ib, winner_is_a = _index_battles(battles)
    n_models = len(models)
    n_battles = len(battles)

    all_elos = np.empty((n_samples, n_models))
    rng = np.random.default_rng()

    for s in range(n_samples):
        idx = rng.integers(0, n_battles, size=n_battles)
        all_elos[s] = _fit_from_arrays(ia[idx], ib[idx], winner_is_a[idx], n_models)

    medians = np.median(all_elos, axis=0)
    lowers = np.percentile(all_elos, 2.5, axis=0)
    uppers = np.percentile(all_elos, 97.5, axis=0)

    return {
        models[i]: (float(medians[i]), float(lowers[i]), float(uppers[i]))
        for i in range(n_models)
    }
