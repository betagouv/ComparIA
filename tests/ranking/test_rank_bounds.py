"""
Tests for the rank interval read from the bootstrap rounds
(utils/ranking/compute._bootstrap_rank_bounds and its use in _compute_ranking).

DB-free. Runnable either way:
    LANGUIA_DEBUG=true uv run python tests/ranking/test_rank_bounds.py
    pytest tests/ranking/test_rank_bounds.py
"""

import random
import sys
from pathlib import Path
from uuid import uuid4

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.ranking.bradley_terry import Interval  # noqa: E402
from utils.ranking.compute import (  # noqa: E402
    _bootstrap_rank_bounds,
    _compute_ranking,
    _variant_table,
)

nan = float("nan")


def _bounds(rounds):
    best, worst = _bootstrap_rank_bounds(np.array(rounds, dtype=float))
    return best.tolist(), worst.tolist()


def test_same_order_every_round_gives_exact_ranks():
    rounds = [[1100, 1000, 900]] * 100
    assert _bounds(rounds) == ([1, 2, 3], [1, 2, 3])


def test_models_that_swap_often_share_both_places():
    rounds = [[1010, 1000, 900]] * 50 + [[1000, 1010, 900]] * 50
    assert _bounds(rounds) == ([1, 1, 3], [2, 2, 3])


def test_rare_swap_stays_outside_the_interval():
    # Two intervals that overlap, but B beats A in only 1 round out of 100:
    # the old overlap rule would give both models places 1 to 2.
    rounds = [[1100, 1000]] * 99 + [[1000, 1100]]
    assert _bounds(rounds) == ([1, 2], [1, 2])


def test_swap_in_more_than_2_5_percent_of_rounds_counts():
    rounds = [[1100, 1000]] * 96 + [[1000, 1100]] * 4
    assert _bounds(rounds) == ([1, 1], [2, 2])


def test_missing_rating_neither_ranks_nor_pushes_others_down():
    rounds = [[1100, nan, 900]] * 50 + [[1100, 1000, 900]] * 50
    best, worst = _bounds(rounds)
    assert (best[0], worst[0]) == (1, 1)
    # Ranked only in the rounds where it has a rating.
    assert (best[1], worst[1]) == (2, 2)
    # Second in the rounds where the middle model is missing.
    assert (best[2], worst[2]) == (2, 3)


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


def _crowded_votes(models, n=3000, seed=0):
    """Evenly spaced strengths, close enough that neighbours' scores overlap."""
    rng = random.Random(seed)
    strength = {m: 1000 - 15 * i for i, m in enumerate(models)}
    votes = []
    for _ in range(n):
        a, b = rng.sample(models, 2)
        p_a = 1 / (1 + 10 ** ((strength[b] - strength[a]) / 400))
        votes.append(_vote(a, b, rng.random() < p_a))
    return votes


def test_point_rank_always_inside_its_interval():
    # The full-data fit puts A first, but B leads in every bootstrap round.
    a, b = uuid4(), uuid4()
    rounds = np.array([[1000.0, 1010.0]] * 100)
    table = _variant_table(
        {
            a: Interval(1010.0, 1000.0, 1000.0, rounds[:, 0]),
            b: Interval(1000.0, 1010.0, 1010.0, rounds[:, 1]),
        },
        {},
        {},
    )
    bounds = {m: (t["rank_p2_5"], t["rank"], t["rank_p97_5"]) for m, t in table.items()}
    assert bounds == {a: (1, 1, 2), b: (1, 2, 2)}


def test_interval_narrower_than_score_overlap():
    """
    The interval answers "where does this model rank in 95% of rounds", which is
    tighter than "whose score interval touches this one".
    """
    models = [uuid4() for _ in range(12)]
    result = _compute_ranking(_crowded_votes(models), {}, with_ratio=False)
    views = list(result.rankings.values())

    def overlap_width(view):
        touching = sum(
            1
            for other in views
            if other.score_p2_5 <= view.score_p97_5
            and view.score_p2_5 <= other.score_p97_5
        )
        return touching - 1

    assert sum(v.rank_p97_5 - v.rank_p2_5 for v in views) < sum(
        overlap_width(v) for v in views
    )


if __name__ == "__main__":
    test_same_order_every_round_gives_exact_ranks()
    test_models_that_swap_often_share_both_places()
    test_rare_swap_stays_outside_the_interval()
    test_swap_in_more_than_2_5_percent_of_rounds_counts()
    test_missing_rating_neither_ranks_nor_pushes_others_down()
    test_point_rank_always_inside_its_interval()
    test_interval_narrower_than_score_overlap()
    print("ok")
