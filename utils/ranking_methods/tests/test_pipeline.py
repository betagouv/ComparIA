# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

from unittest.mock import patch

import polars as pl
import pytest

from rank_comparia.pipeline import Match, RankingPipeline


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


def test_init_pipeline_with_votes_only(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=5,
        mean_how="match",
        export_path=None,
    )
    # matches should come from mocked sample_df
    assert isinstance(pipeline.matches, pl.DataFrame)
    assert not pipeline.matches.is_empty()
    mock_load_comparia.assert_called_once_with("ministere-culture/comparia-votes")


def test_init_pipeline_with_reactions_only(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=False,
        include_reactions=True,
        bootstrap_samples=5,
        mean_how="match",
        export_path=None,
    )
    assert isinstance(pipeline.matches, pl.DataFrame)
    assert not pipeline.matches.is_empty()
    mock_load_comparia.assert_called_once_with("ministere-culture/comparia-reactions")


def test_run_returns_dataframe(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=3,
        mean_how="match",
        export_path=None,
    )
    scores = pipeline.run()
    assert isinstance(scores, pl.DataFrame)
    assert "model_name" in scores.columns


def test_run_category(mock_load_comparia):
    pipeline = RankingPipeline(
        method="elo_random",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=3,
        mean_how="match",
    )
    category = "Law & Justice"
    scores = pipeline.run_category(category)
    assert isinstance(scores, pl.DataFrame)
    assert "model_name" in scores.columns


def test_run_all_categories_skips_if_too_few_matches(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=2,
        mean_how="match",
    )
    results = pipeline.run_all_categories()
    assert isinstance(results, dict)
    assert results == {}


def test_process_reactions_data(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=2,
        mean_how="match",
    )
    matches = pipeline._process_reactions_data()
    assert isinstance(matches, pl.DataFrame)
    assert "score" in matches.columns
    assert len(matches) == 5


def test_process_votes_data(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=False,
        include_reactions=True,
        bootstrap_samples=2,
        mean_how="match",
    )
    matches = pipeline._process_votes_data()
    assert isinstance(matches, pl.DataFrame)
    assert "score" in matches.columns
    assert len(matches) == 10


def test_votes_match_list(mock_load_comparia):
    pipeline = RankingPipeline(
        method="ml",
        include_votes=True,
        include_reactions=False,
        bootstrap_samples=2,
        mean_how="match",
    )
    matches = pipeline.match_list()
    assert isinstance(matches, list)
    assert isinstance(matches[0], Match)
    assert len(matches) == 10
