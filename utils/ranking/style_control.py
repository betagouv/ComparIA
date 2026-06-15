"""
Style-controlled Bradley-Terry model.

The plain Bradley-Terry fit in ``bradley_terry.py`` treats every win equally,
so a model can climb the leaderboard purely by answering at greater length or
with heavier markdown formatting (headers, bold, bullet lists) rather than by
being more correct. This module removes that confound the same way the LMArena
"Style Control" does: it fits a logistic regression whose design matrix is the
usual per-model strength indicators *augmented* with a handful of presentation
features (the normalized A-vs-B difference in length and markdown density).

The presentation coefficients absorb the part of the vote explained by style,
so the per-model strengths become a *style-debiased* Elo: what the ranking
would look like if both answers were formatted identically.

Pure numpy (Newton-Raphson / IRLS) to avoid a scipy/sklearn dependency, mirroring
the MM solver next door. The public surface matches ``bradley_terry.py`` so the
two are drop-in compatible for the ranking pipeline.
"""

import re

import numpy as np

# --------------------------------------------------------------------------- #
# Style feature extraction
# --------------------------------------------------------------------------- #

# Markdown atx headers (## ...), up to three leading spaces per CommonMark.
_HEADER_RE = re.compile(r"^ {0,3}#{1,6}\s", re.MULTILINE)
# Ordered or unordered list items.
_LIST_RE = re.compile(r"^ {0,3}([-*+]|\d+[.)])\s", re.MULTILINE)

# Order matters: it is the column order of the style design matrix and of the
# coefficients reported back to callers.
STYLE_FEATURES: tuple[str, ...] = ("length", "md_headers", "md_bold", "md_lists")


def markdown_counts(content: str | None) -> tuple[int, int, int]:
    """Return (headers, bold_spans, list_items) for one assistant answer."""
    if not content:
        return 0, 0, 0
    headers = len(_HEADER_RE.findall(content))
    bold = content.count("**") // 2
    lists = len(_LIST_RE.findall(content))
    return headers, bold, lists


def style_vector(content: str | None, tokens: int | None) -> np.ndarray:
    """Raw style measurements for one answer, ordered like ``STYLE_FEATURES``."""
    headers, bold, lists = markdown_counts(content)
    length = float(tokens) if tokens and tokens > 0 else 0.0
    return np.array([length, headers, bold, lists], dtype=float)


def _normalized_standardized_diffs(
    style_a: np.ndarray, style_b: np.ndarray
) -> np.ndarray:
    """
    Turn raw per-answer style measurements into model-agnostic regressors.

    For each feature we take the *normalized* difference (a - b) / (a + b) so a
    long answer beating a short one looks the same whether both are 50 or 5000
    tokens, then standardize each column to unit variance so the logistic
    coefficients are directly comparable across features.

    Args:
        style_a, style_b: (n_battles, n_features) raw measurements for the A and
            B answer of each battle.

    Returns:
        (n_battles, n_features) standardized difference matrix. All-zero columns
        (a feature that never varies) are left at zero rather than divided by 0.
    """
    denom = style_a + style_b
    diff = np.divide(
        style_a - style_b, denom, out=np.zeros_like(denom), where=denom > 0
    )
    std = diff.std(axis=0)
    std[std == 0] = 1.0
    return (diff - diff.mean(axis=0)) / std


# --------------------------------------------------------------------------- #
# Logistic Bradley-Terry solver with style covariates
# --------------------------------------------------------------------------- #


def _fit_logistic(
    ia: np.ndarray,
    ib: np.ndarray,
    winner_is_a: np.ndarray,
    style: np.ndarray,
    n: int,
    ridge: float = 1e-3,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Fit ``P(a beats b) = sigmoid(beta_a - beta_b + style . gamma)`` by Newton's
    method and return ``(elo, gamma)``.

    ``beta`` are per-model log-strengths, ``gamma`` the style coefficients. As in
    the MM solver, models that never won or never lost are degenerate (their MLE
    is ±inf) so they are dropped from the fit and returned as NaN; callers (the
    bootstrap especially) can then ignore them instead of treating them as wild
    outliers.

    A small ridge penalty fixes the additive gauge freedom of the per-model
    indicators (adding a constant to every ``beta`` leaves the likelihood
    unchanged) and keeps the Hessian positive-definite for sparsely observed
    models; it is negligible for well-observed ones.
    """
    k = style.shape[1]
    elo = np.full(n, np.nan)

    wins = np.bincount(ia, weights=winner_is_a, minlength=n) + np.bincount(
        ib, weights=~winner_is_a, minlength=n
    )
    appearances = np.bincount(ia, minlength=n) + np.bincount(ib, minlength=n)
    present = (appearances > 0) & (wins > 0) & (wins < appearances)
    if not present.any():
        return elo, np.zeros(k)

    # Reindex battles onto the present-models-only sub-problem. A battle is kept
    # only if both of its models are non-degenerate.
    remap = np.full(n, -1)
    remap[present] = np.arange(present.sum())
    m = int(present.sum())
    ja, jb = remap[ia], remap[ib]
    keep = (ja >= 0) & (jb >= 0)
    ja, jb, style = ja[keep], jb[keep], style[keep]
    y = winner_is_a[keep].astype(float)
    # Parameter vector theta = [beta (m) | gamma (k)].
    theta = np.zeros(m + k)

    for _ in range(max_iter):
        beta, gamma = theta[:m], theta[m:]
        logits = beta[ja] - beta[jb] + style @ gamma
        p = 1.0 / (1.0 + np.exp(-logits))
        w = p * (1.0 - p)
        resid = y - p

        # Gradient of the penalized log-likelihood.
        g = np.empty(m + k)
        g[:m] = (
            np.bincount(ja, weights=resid, minlength=m)
            - np.bincount(jb, weights=resid, minlength=m)
            - ridge * beta
        )
        g[m:] = style.T @ resid - ridge * gamma

        # Hessian (negative): H = X^T diag(w) X + ridge*I, built blockwise to
        # exploit the +1/-1 sparsity of the per-model indicator block.
        H = np.zeros((m + k, m + k))
        diag = np.bincount(ja, weights=w, minlength=m) + np.bincount(
            jb, weights=w, minlength=m
        )
        bb = H[:m, :m]
        bb[np.arange(m), np.arange(m)] = diag
        np.add.at(bb, (ja, jb), -w)
        np.add.at(bb, (jb, ja), -w)

        ws = w[:, None] * style
        cross = np.zeros((m, k))  # beta-gamma block
        for c in range(k):
            cross[:, c] = np.bincount(ja, weights=ws[:, c], minlength=m) - np.bincount(
                jb, weights=ws[:, c], minlength=m
            )
        H[:m, m:] = cross
        H[m:, :m] = cross.T
        H[m:, m:] = style.T @ ws
        H[np.arange(m + k), np.arange(m + k)] += ridge

        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, g, rcond=None)[0]
        theta += step
        if np.max(np.abs(step)) < tol:
            break

    beta = theta[:m]
    beta -= beta.mean()  # center, then map log-strength -> Elo points
    elo[present] = 400.0 / np.log(10.0) * beta
    elo[present] += 1000.0
    return elo, theta[m:]


def fit_style_controlled(
    battles: list[tuple[str, str, str]],
    style_a: np.ndarray,
    style_b: np.ndarray,
    ridge: float = 1e-3,
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Style-controlled Bradley-Terry point estimate.

    Args:
        battles: (model_a, model_b, winner) tuples; winner is model_a or model_b.
        style_a, style_b: (n_battles, n_features) raw style measurements aligned
            row-for-row with ``battles`` (see ``style_vector``).
        ridge: L2 strength for gauge-fixing / regularization.

    Returns:
        (elo_by_model, style_coefficients) where style_coefficients maps each
        name in ``STYLE_FEATURES`` to its logistic coefficient (positive = that
        presentation axis independently raises an answer's win probability).
    """
    if not battles:
        return {}, {f: 0.0 for f in STYLE_FEATURES}

    models = sorted({m for b in battles for m in (b[0], b[1])})
    idx = {m: i for i, m in enumerate(models)}
    ia = np.fromiter((idx[b[0]] for b in battles), dtype=int, count=len(battles))
    ib = np.fromiter((idx[b[1]] for b in battles), dtype=int, count=len(battles))
    winner_is_a = np.fromiter(
        (b[2] == b[0] for b in battles), dtype=bool, count=len(battles)
    )

    style = _normalized_standardized_diffs(style_a, style_b)
    elo, gamma = _fit_logistic(ia, ib, winner_is_a, style, len(models), ridge=ridge)
    return (
        dict(zip(models, elo.tolist())),
        dict(zip(STYLE_FEATURES, gamma.tolist())),
    )


def bootstrap_style_controlled(
    battles: list[tuple[str, str, str]],
    style_a: np.ndarray,
    style_b: np.ndarray,
    n_samples: int = 200,
    ridge: float = 1e-3,
) -> tuple[dict[str, tuple[float, float, float]], dict[str, float]]:
    """
    Style-controlled ratings with bootstrap confidence intervals.

    Mirrors ``bradley_terry.bootstrap_confidence_intervals``: the displayed Elo
    is the single full-data point estimate (not the bootstrap median), and the
    bootstrap is used only for the 2.5/97.5 percentile bounds. Rounds where a
    model is absent / undefeated / winless contribute NaN and are dropped from
    that model's percentile.

    Returns:
        (ci_by_model, style_coefficients) where ci_by_model maps model -> (point,
        lower_2.5, upper_97.5).
    """
    if not battles:
        return {}, {f: 0.0 for f in STYLE_FEATURES}

    models = sorted({m for b in battles for m in (b[0], b[1])})
    idx = {m: i for i, m in enumerate(models)}
    n_models = len(models)
    n_battles = len(battles)
    ia = np.fromiter((idx[b[0]] for b in battles), dtype=int, count=n_battles)
    ib = np.fromiter((idx[b[1]] for b in battles), dtype=int, count=n_battles)
    winner_is_a = np.fromiter(
        (b[2] == b[0] for b in battles), dtype=bool, count=n_battles
    )
    style = _normalized_standardized_diffs(style_a, style_b)

    point_elo, gamma = _fit_logistic(ia, ib, winner_is_a, style, n_models, ridge=ridge)

    all_elos = np.empty((n_samples, n_models))
    rng = np.random.default_rng()
    for s in range(n_samples):
        sel = rng.integers(0, n_battles, size=n_battles)
        all_elos[s], _ = _fit_logistic(
            ia[sel], ib[sel], winner_is_a[sel], style[sel], n_models, ridge=ridge
        )

    lowers = np.nanpercentile(all_elos, 2.5, axis=0)
    uppers = np.nanpercentile(all_elos, 97.5, axis=0)
    ci = {
        models[i]: (float(point_elo[i]), float(lowers[i]), float(uppers[i]))
        for i in range(n_models)
    }
    return ci, dict(zip(STYLE_FEATURES, gamma.tolist()))
