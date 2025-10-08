# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import polars as pl
import pytest

from rank_comparia.maximum_likelihood import MaximumLikelihoodRanker
from rank_comparia.pipeline import RankingPipeline


@pytest.fixture(name="conversations")
def fixture_conversations():
    return pl.read_parquet("tests/data/sample_comparia_conversations.parquet")


@pytest.fixture(name="mock_load_comparia")
def fixture_load_comparia(conversations):
    sample_votes = pl.read_parquet("tests/data/sample_comparia_votes.parquet")
    sample_reactions = pl.read_parquet("tests/data/sample_comparia_reactions.parquet")

    def _side_effect(arg):
        if arg == "ministere-culture/comparia-votes":
            return sample_votes.join(conversations, on="conversation_pair_id", coalesce=True)
        elif arg == "ministere-culture/comparia-reactions":
            return sample_reactions.join(conversations, on="conversation_pair_id", coalesce=True)

    with patch("rank_comparia.pipeline.load_comparia", side_effect=_side_effect) as mock_fn:
        yield mock_fn


@pytest.fixture(name="votes_match_list")
def fixture_votes_match_list(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=2,
        mean_how="match",
    )
    return pipeline.match_list()


def test_empty_scores_at_init():
    ranker = MaximumLikelihoodRanker()
    assert ranker.get_scores() == {}


def test_aggregate_matches(votes_match_list):
    ranker = MaximumLikelihoodRanker()
    agg = ranker.aggregate_matches(votes_match_list)
    assert isinstance(agg, pl.DataFrame)
    assert len(agg) == 20


def test_compute_scores_returns_dict(votes_match_list):
    ranker = MaximumLikelihoodRanker()
    scores = ranker.compute_scores(votes_match_list)
    assert isinstance(scores, dict)
    assert len(scores) == 15
