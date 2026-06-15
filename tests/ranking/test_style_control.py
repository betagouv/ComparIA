"""
Tests for the style-controlled Bradley-Terry solver (utils/ranking/style_control).

Deterministic and DB-free. Runnable either way:
    uv run python tests/ranking/test_style_control.py
    pytest tests/ranking/test_style_control.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.ranking.style_control import (  # noqa: E402
    STYLE_FEATURES,
    fit_style_controlled,
    markdown_counts,
    style_vector,
)

RICH = (
    "## Heading\nIntro with **bold** and **strong** text.\n- a\n- b\n1. c\n" + "x" * 400
)
PLAIN = "Oui, c'est une bonne reponse."


def test_markdown_counts():
    headers, bold, lists = markdown_counts(RICH)
    assert headers == 1
    assert bold == 2  # two "**...**" spans; "__"-style is deliberately ignored
    assert lists == 3  # two "-" items + one "1." item
    # "__"-style bold is not counted, to avoid false positives on code like __init__
    assert markdown_counts("call __init__ and __main__")[1] == 0
    assert markdown_counts(None) == (0, 0, 0)
    assert markdown_counts("") == (0, 0, 0)


def test_style_vector_length_from_tokens():
    v = style_vector(PLAIN, tokens=42)
    assert v[0] == 42.0
    assert style_vector(PLAIN, tokens=None)[0] == 0.0
    assert style_vector(PLAIN, tokens=0)[0] == 0.0


def _synthetic_battles(n=6000, seed=0):
    """
    Four equally-strong models. ``show_off`` formats richly 90% of the time, the
    others 50%. The richer-formatted answer wins with probability 0.7,
    independent of model identity -> a pure style effect that plain Bradley-Terry
    would misattribute to ``show_off`` being a better model.
    """
    rng = np.random.default_rng(seed)
    models = {"show_off": 0.9, "m1": 0.5, "m2": 0.5, "m3": 0.5}
    names = list(models)
    battles, style_a, style_b = [], [], []
    for _ in range(n):
        a, b = rng.choice(names, size=2, replace=False)
        rich_a = rng.random() < models[a]
        rich_b = rng.random() < models[b]
        if rich_a == rich_b:
            a_wins = rng.random() < 0.5
        else:
            richer_is_a = rich_a and not rich_b
            a_wins = richer_is_a == (rng.random() < 0.7)
        battles.append((a, b, a if a_wins else b))
        style_a.append(style_vector(RICH if rich_a else PLAIN, 600 if rich_a else 15))
        style_b.append(style_vector(RICH if rich_b else PLAIN, 600 if rich_b else 15))
    return battles, np.array(style_a), np.array(style_b)


def test_style_coefficients_positive():
    battles, sa, sb = _synthetic_battles()
    _, coeffs = fit_style_controlled(battles, sa, sb)
    assert set(coeffs) == set(STYLE_FEATURES)
    # richer formatting was constructed to help win -> positive style pressure
    assert sum(coeffs.values()) > 0
    assert all(np.isfinite(v) for v in coeffs.values())


def test_style_control_deflates_inflated_model():
    from utils.ranking.bradley_terry import fit_bradley_terry

    battles, sa, sb = _synthetic_battles()
    plain = fit_bradley_terry(battles)
    controlled, _ = fit_style_controlled(battles, sa, sb)

    # Plain BT over-credits the heavy formatter; style control moves it back
    # toward the (equally strong) pack.
    others = [m for m in controlled if m != "show_off"]
    plain_gap = plain["show_off"] - np.mean([plain[m] for m in others])
    ctrl_gap = controlled["show_off"] - np.mean([controlled[m] for m in others])
    assert plain_gap > ctrl_gap
    assert plain_gap > 15  # the bias is clearly visible without control


def test_matches_plain_bradley_terry_when_style_is_neutral():
    from utils.ranking.bradley_terry import fit_bradley_terry

    # Identical style on both sides of every battle -> the style regressors are
    # all zero, so the style-controlled fit must reproduce the plain MM Bradley-
    # Terry ranking. This guards the production swap of MM for this Newton solver:
    # when presentation is neutral the leaderboard must not move.
    battles, _, _ = _synthetic_battles()
    n = len(battles)
    flat = np.ones((n, len(STYLE_FEATURES)))

    elo, coeffs = fit_style_controlled(battles, flat, flat)
    plain = fit_bradley_terry(battles)

    assert all(v == 0.0 for v in coeffs.values())  # no style signal to absorb
    assert max(abs(elo[m] - plain[m]) for m in plain) < 0.01


def test_style_regressor_is_antisymmetric():
    from utils.ranking.style_control import _style_regressors

    # Swapping the A and B answers must flip the regressor's sign exactly, the
    # antisymmetry a Bradley-Terry style term requires (no mean-centering bias).
    sa = np.array([[600.0, 2, 3, 4], [15.0, 0, 0, 0], [120.0, 1, 0, 2]])
    sb = np.array([[15.0, 0, 0, 0], [300.0, 1, 1, 1], [120.0, 1, 0, 2]])
    np.testing.assert_allclose(
        _style_regressors(sa, sb), -_style_regressors(sb, sa), atol=1e-12
    )


def test_degenerate_models_return_nan():
    # "always_wins" never loses -> Bradley-Terry MLE is degenerate -> NaN.
    battles = [("always_wins", "loser", "always_wins")] * 50
    battles += [("loser", "mid", "mid")] * 50
    battles += [("mid", "other", "other")] * 50
    battles += [("other", "loser", "other")] * 50
    n = len(battles)
    sa = np.ones((n, len(STYLE_FEATURES)))
    sb = np.ones((n, len(STYLE_FEATURES)))
    elo, _ = fit_style_controlled(battles, sa, sb)
    assert np.isnan(elo["always_wins"])


def test_empty_input():
    elo, coeffs = fit_style_controlled([], np.empty((0, 4)), np.empty((0, 4)))
    assert elo == {}
    assert coeffs == {f: 0.0 for f in STYLE_FEATURES}


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"ok  {fn.__name__}")
    print(f"\nAll {len(fns)} tests passed.")
