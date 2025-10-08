# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

import polars as pl
import pytest

from rank_comparia.data_transformation import get_matches_with_score, get_winners, get_winrates


@pytest.fixture(name="data")
def fixture_data():
    return pl.read_parquet("tests/data/sample_comparia_reactions.parquet")


def test_get_matches_with_score(data):
    scores = get_matches_with_score(data)

    # 1st conv pair
    result = pl.DataFrame(
        {
            "score_a": [1],
            "score_b": [0],
        }
    )
    assert (
        scores.filter(
            pl.col("conversation_pair_id") == "0ef1f13f08164087bd7e7f55063b9942-aabde2b84e6744e295831d4036103d1c"
        )
        .select(["score_a", "score_b"])
        .equals(result)
    )

    # 2nd conv pair
    result = pl.DataFrame(
        {
            "score_a": [0],
            "score_b": [1],
        }
    )
    assert (
        scores.filter(
            pl.col("conversation_pair_id") == "ad8b11aecd1e457ebebfa6d4d93a8168-40bce3550d8f475ea3f2ed8f6518f722"
        )
        .select(["score_a", "score_b"])
        .equals(result)
    )

    # 3rd conv pair
    result = pl.DataFrame(
        {
            "score_a": [-1],
            "score_b": [0],
        }
    )
    assert (
        scores.filter(
            pl.col("conversation_pair_id") == "b1a12e07607c44c280616489204f5ade-2f0d3df44d2e45fcaa9df94e5c63af11"
        )
        .select(["score_a", "score_b"])
        .equals(result)
    )


def test_get_winners(data):
    scores = get_matches_with_score(data)
    winners = get_winners(scores)

    # 1st conv pair
    assert (
        winners.filter(
            pl.col("conversation_pair_id") == "0ef1f13f08164087bd7e7f55063b9942-aabde2b84e6744e295831d4036103d1c"
        )["model_name"].item()
        == "gemini-2.0-flash-001"
    )

    # 2nd conv pair
    assert (
        winners.filter(
            pl.col("conversation_pair_id") == "ad8b11aecd1e457ebebfa6d4d93a8168-40bce3550d8f475ea3f2ed8f6518f722"
        )["model_name"].item()
        == "command-a"
    )

    # 3rd conv pair
    assert (
        winners.filter(
            pl.col("conversation_pair_id") == "b1a12e07607c44c280616489204f5ade-2f0d3df44d2e45fcaa9df94e5c63af11"
        )["model_name"].item()
        == "mistral-large-2411"
    )


def test_get_winrates(data):
    scores = get_matches_with_score(data)
    winners = get_winners(scores)
    winrates = get_winrates(winners)

    # winrate of mistral-large-2411
    assert winrates.filter(pl.col("model_name") == "mistral-large-2411")["winrate"].item() == 100.0

    # winrate of claude-3-5-sonnet-v2
    assert winrates.filter(pl.col("model_name") == "claude-3-5-sonnet-v2")["winrate"].item() == 0.0
