"""
Tests for the max rank spread applied when building the ranking table
(utils/ranking/compute._shown_models and its use in _compute_ranking).

The leaderboard hides models whose rank may move more than max_rank_spread
places. Those hidden models must not widen the shown models' rank ranges.

DB-free. Runnable either way:
    uv run python tests/ranking/test_rank_spread.py
    pytest tests/ranking/test_rank_spread.py
"""

import asyncio
import random
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.ranking import compute  # noqa: E402
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

    shown, _ = _shown_models(ci, table, 0)
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
        shown, _ = _shown_models(ci, _variant_table(ci, {}, {}), spread)
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


def test_a_hidden_model_stays_over_the_spread(monkeypatch):
    # Found by search: one model dropped on the way falls back under the spread
    # once every other hidden model is counted again.
    rng = random.Random(663)
    ci = {}
    for i in range(60):
        centre = rng.uniform(800, 1200)
        width = rng.choice((5, 15, 30, 80, 150))
        samples = np.random.default_rng(663_000 + i).normal(centre, width, 1000)
        ci[uuid4()] = Interval(
            centre,
            float(np.percentile(samples, 2.5)),
            float(np.percentile(samples, 97.5)),
            samples,
        )
    monkeypatch.setattr(compute, "bootstrap_style_controlled", lambda *_: (ci, {}))
    monkeypatch.setattr(compute, "bootstrap_confidence_intervals", lambda _: ci)
    models = list(ci)
    votes = [_vote(a, b, True) for a, b in zip(models, models[1:])]

    result = _compute_ranking(votes, {}, with_ratio=False, max_rank_spread=10)

    # The leaderboard's filter, then its numbering.
    shown = [r for r in result.rankings.values() if max(r.trust_range) <= 10]
    assert shown
    assert sorted(r.rank for r in shown) == list(range(1, len(shown) + 1))


def test_ranking_keeps_the_spread_it_was_counted_with():
    result = _compute_ranking(_votes(), {}, with_ratio=False, max_rank_spread=12)
    assert result.max_rank_spread == 12


def _llms_list(ranking, setting: int):
    from backend.llms import data
    from backend.llms.currency import CurrencyInfo

    async def llms_data():
        return SimpleNamespace(all={})

    async def currency():
        return CurrencyInfo(code="EUR", rate_from_usd=1.0, date=None, source="base")

    async def app_settings():
        return SimpleNamespace(
            ranking_max_rank_spread=setting, ranking_grey_rank_spread=setting
        )

    patches = {
        "get_llms_data": llms_data,
        "get_ranking": lambda: ranking,
        "get_currency_info": currency,
        "get_app_settings": app_settings,
    }
    saved = {name: getattr(data, name) for name in patches}
    for name, value in patches.items():
        setattr(data, name, value)
    try:
        return asyncio.run(data.get_llms_list())
    finally:
        for name, value in saved.items():
            setattr(data, name, value)


def test_leaderboard_filters_with_the_ranking_spread_not_the_new_setting():
    # The admin raised the spread after the last run: the ranks on hand were
    # counted for 10, so the leaderboard must keep filtering with 10.
    ranking = compute.RankingResult(timestamp=0.0, max_rank_spread=10)
    assert _llms_list(ranking, setting=40).max_rank_spread == 10


def test_leaderboard_falls_back_to_the_setting_for_an_older_ranking():
    ranking = compute.RankingResult(timestamp=0.0)
    assert _llms_list(ranking, setting=40).max_rank_spread == 40
    assert _llms_list(None, setting=40).max_rank_spread == 40


if __name__ == "__main__":
    test_noisy_model_is_hidden_and_others_rank_among_themselves()
    test_shown_models_always_fit_the_spread()
    test_hidden_model_does_not_widen_the_shown_ranges()
