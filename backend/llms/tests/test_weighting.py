"""
Tests for weighted model sampling.

Run with:
    .venv/bin/python -m unittest backend.llms.tests.test_weighting
"""

import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from backend.config import settings
from backend.llms.weighting import compute_weights


def _mock_ranking(counts: dict[str, int]):
    rankings = {m: SimpleNamespace(n_match=n) for m, n in counts.items()}
    return SimpleNamespace(rankings=rankings)


class ComputeWeightsTest(unittest.TestCase):
    def setUp(self):
        self._prev_enabled = settings.WEIGHTED_SAMPLING_ENABLED
        settings.WEIGHTED_SAMPLING_ENABLED = True

    def tearDown(self):
        settings.WEIGHTED_SAMPLING_ENABLED = self._prev_enabled

    def test_under_voted_model_gets_higher_weight(self):
        ranking = _mock_ranking({"new": 10, "mid": 500, "old": 5000})
        w = compute_weights(["new", "mid", "old"], ranking)
        assert w is not None
        self.assertGreater(w[0], w[1])
        self.assertGreater(w[1], w[2])
        self.assertAlmostEqual(float(w.sum()), 1.0, places=9)

    def test_max_ratio_clip_enforced(self):
        ranking = _mock_ranking({"brand_new": 0, "ancient": 1_000_000})
        w = compute_weights(["brand_new", "ancient"], ranking)
        assert w is not None
        self.assertLessEqual(
            w.max() / w.min(), settings.WEIGHTED_SAMPLING_MAX_RATIO + 1e-9
        )

    def test_zero_vote_model_doesnt_blow_up(self):
        ranking = _mock_ranking({"a": 0, "b": 0})
        w = compute_weights(["a", "b"], ranking)
        assert w is not None
        self.assertTrue(np.isfinite(w).all())
        self.assertAlmostEqual(float(w[0]), 0.5)
        self.assertAlmostEqual(float(w[1]), 0.5)

    def test_flag_off_returns_none(self):
        settings.WEIGHTED_SAMPLING_ENABLED = False
        self.assertIsNone(compute_weights(["a", "b"], _mock_ranking({"a": 10})))

    def test_missing_ranking_returns_none(self):
        self.assertIsNone(compute_weights(["a", "b"], None))

    def test_model_missing_from_ranking_uses_zero_matches(self):
        # A brand-new model won't be in the ranking yet; it should still
        # get a weight (treated as 0 matches = highest weight).
        ranking = _mock_ranking({"known": 1000})
        w = compute_weights(["brand_new", "known"], ranking)
        assert w is not None
        self.assertGreater(w[0], w[1])


class SamplingDistributionTest(unittest.TestCase):
    def test_empirical_distribution_matches_weights(self):
        ranking = _mock_ranking({"new": 10, "mid": 500, "old": 5000})
        pool = ["new", "mid", "old"]
        w = compute_weights(pool, ranking)

        assert w is not None
        rng = np.random.default_rng(42)
        picks = Counter(pool[rng.choice(len(pool), p=w)] for _ in range(10_000))

        for i, m in enumerate(pool):
            empirical = picks[m] / 10_000
            expected = float(w[i])
            self.assertAlmostEqual(empirical, expected, delta=0.02)


if __name__ == "__main__":
    unittest.main()
