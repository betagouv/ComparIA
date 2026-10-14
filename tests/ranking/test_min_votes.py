"""
Tests for the vote minimum applied when building the ranking table
(utils/ranking/compute._compute_ranking).

DB-free. Runnable either way:
    uv run python tests/ranking/test_min_votes.py
    pytest tests/ranking/test_min_votes.py
"""

import random
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.ranking.compute import _compute_ranking  # noqa: E402

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
        votes.append(_vote(STRONG, MEDIUM, rng.random() < 0.7))
        votes.append(_vote(MEDIUM, WEAK, rng.random() < 0.7))
        votes.append(_vote(STRONG, WEAK, rng.random() < 0.85))
    # Few votes, so its interval is wide enough to overlap everyone.
    votes += [_vote(RARE, WEAK, True), _vote(RARE, STRONG, False)] * 3
    return votes


def test_no_minimum_ranks_every_model():
    result = _compute_ranking(_votes(), {}, with_ratio=False)
    assert set(result.rankings) == {STRONG, MEDIUM, WEAK, RARE}


def test_minimum_leaves_out_models_below_it():
    result = _compute_ranking(_votes(), {}, with_ratio=False, min_votes=50)
    assert set(result.rankings) == {STRONG, MEDIUM, WEAK}
    assert sorted(r.rank for r in result.rankings.values()) == [1, 2, 3]
    assert all(r.rank_p97_5 <= 3 for r in result.rankings.values())
    # Uncontrolled view is filtered the same way.
    assert sorted(r.uncontrolled.rank for r in result.rankings.values()) == [1, 2, 3]
    assert all(r.uncontrolled.rank_p97_5 <= 3 for r in result.rankings.values())


def test_models_below_minimum_still_count_in_the_fit():
    """RARE's battles stay in the fit, so their opponents' vote counts include them."""
    result = _compute_ranking(_votes(), {}, with_ratio=False, min_votes=50)
    assert result.rankings[WEAK].n_match == 400 + 3
    # Same fit as with no minimum, so the point scores do not move.
    unfiltered = _compute_ranking(_votes(), {}, with_ratio=False)
    for model in (STRONG, MEDIUM, WEAK):
        assert result.rankings[model].elo == unfiltered.rankings[model].elo
        assert (
            result.rankings[model].uncontrolled.elo
            == unfiltered.rankings[model].uncontrolled.elo
        )


if __name__ == "__main__":
    test_no_minimum_ranks_every_model()
    test_minimum_leaves_out_models_below_it()
    test_models_below_minimum_still_count_in_the_fit()
    print("ok")
