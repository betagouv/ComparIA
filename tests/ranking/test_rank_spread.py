"""
Tests for the max rank spread applied when building the ranking table
(utils/ranking/compute._shown_models and its use in _compute_ranking).

The leaderboard hides models whose rank may move more than max_rank_spread
places. Those hidden models must not widen the shown models' rank ranges.

DB-free. Runnable either way:
    uv run python tests/ranking/test_rank_spread.py
    pytest tests/ranking/test_rank_spread.py
"""

import random
import sys
from pathlib import Path
from uuid import uuid4

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.ranking.bradley_terry import Interval  # noqa: E402
from utils.ranking.compute import (  # noqa: E402
    _compute_ranking,
    _over_spread,
    _shown_models,
    _variant_table,
)

ROUNDS = 200


def _fixed(rating):
    samples = np.full(ROUNDS, float(rating))
    return Interval(rating, rating, rating, samples)


def _noisy(seed, low=500, high=1500):
    samples = np.random.default_rng(seed).uniform(low, high, ROUNDS)
    return Interval(
        float(np.median(samples)),
        float(np.percentile(samples, 2.5)),
        float(np.percentile(samples, 97.5)),
        samples,
    )


def test_noisy_model_is_hidden_and_others_rank_among_themselves():
    solid = {uuid4(): _fixed(r) for r in (1400, 1300, 1200, 1100, 1000)}
    noisy = uuid4()
    ci = solid | {noisy: _noisy(0)}

    table = _variant_table(ci, {}, {})
    # With the noisy model counted, every solid model may move a place.
    assert all(_over_spread(table[m], 0) for m in solid)

    shown = _shown_models(ci, table, 0)
    assert shown == set(solid)

    shown_table = _variant_table({m: ci[m] for m in shown}, {}, {})
    assert sorted(f["rank"] for f in shown_table.values()) == [1, 2, 3, 4, 5]
    assert all(not _over_spread(f, 0) for f in shown_table.values())


def test_shown_models_always_fit_the_spread():
    rng = random.Random(1)
    for spread in (0, 1, 2, 5):
        ci = {}
        for i in range(30):
            centre = rng.uniform(800, 1200)
            width = rng.choice((5, 30, 150))
            samples = np.random.default_rng(i).normal(centre, width, ROUNDS)
            ci[uuid4()] = Interval(
                centre,
                float(np.percentile(samples, 2.5)),
                float(np.percentile(samples, 97.5)),
                samples,
            )
        shown = _shown_models(ci, _variant_table(ci, {}, {}), spread)
        if not shown:
            continue
        final = _variant_table({m: ci[m] for m in shown}, {}, {})
        assert sorted(f["rank"] for f in final.values()) == list(
            range(1, len(shown) + 1)
        )
        assert all(not _over_spread(f, spread) for f in final.values())


STRONG, MEDIUM, WEAK, RARE = (uuid4() for _ in range(4))


def _vote(a, b, a_wins):
    return {
        "choice": "a_better" if a_wins else "b_better",
        "llm_id_a": a,
        "llm_id_b": b,
        "content_a": "answer",
        "content_b": "answer",
        "tokens_a": 50,
        "tokens_b": 50,
        "keyword_annotations_a": [],
        "keyword_annotations_b": [],
    }


def _votes():
    rng = random.Random(0)
    votes = []
    for _ in range(200):
        votes.append(_vote(STRONG, MEDIUM, rng.random() < 0.8))
        votes.append(_vote(MEDIUM, WEAK, rng.random() < 0.8))
        votes.append(_vote(STRONG, WEAK, rng.random() < 0.9))
    # A few votes split both ways, so it could sit anywhere in the table.
    votes += [
        _vote(RARE, STRONG, True),
        _vote(RARE, WEAK, False),
    ] * 2
    return votes


def test_hidden_model_does_not_widen_the_shown_ranges():
    unfiltered = _compute_ranking(_votes(), {}, with_ratio=False)
    assert unfiltered.rankings[RARE].trust_range != [0, 0]

    result = _compute_ranking(_votes(), {}, with_ratio=False, max_rank_spread=0)

    for variant in ("controlled", "uncontrolled"):
        shown = {
            m: (r if variant == "controlled" else r.uncontrolled)
            for m, r in result.rankings.items()
            if m != RARE
        }
        assert sorted(r.rank for r in shown.values()) == [1, 2, 3], variant
        assert all(r.trust_range == [0, 0] for r in shown.values()), variant

    # The hidden model keeps its data and stays over the spread.
    assert result.rankings[RARE].trust_range == unfiltered.rankings[RARE].trust_range


if __name__ == "__main__":
    test_noisy_model_is_hidden_and_others_rank_among_themselves()
    test_shown_models_always_fit_the_spread()
    test_hidden_model_does_not_widen_the_shown_ranges()
