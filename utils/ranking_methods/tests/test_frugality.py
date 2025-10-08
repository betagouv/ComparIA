# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

import polars as pl
import pytest

from rank_comparia.frugality import calculate_frugality_score, get_models_output_tokens, get_n_match


@pytest.fixture(name="data")
def fixture_data():
    data = pl.read_parquet("tests/data/sample_comparia_reactions.parquet")
    return data.rename({"model_a_name": "model_a", "model_b_name": "model_b"})


def test_models_output_tokens(data):
    out_tokens = get_models_output_tokens(data)
    assert len(out_tokens.columns) == 2
    assert out_tokens[0, 1] == 421.0
    assert out_tokens[0, 0] == "claude-3-5-sonnet-v2"


def test_get_n_match(data):
    n_match = get_n_match(data)
    assert len(n_match.columns) == 2
    assert n_match[0, 1] == 1
    assert n_match.shape[0] == 9


def test_calculate_frugal_score(data):
    n_match = pl.read_parquet("tests/data/sample_n_match.parquet")
    frugality_score = calculate_frugality_score(data, n_match)
    assert round(frugality_score[0, "conso_all_conv"], ndigits=5) == 0.01698
    assert len(frugality_score.columns) == 7
    frugality_score = calculate_frugality_score(data, n_match)
    assert round(frugality_score[0, "mean_conso_per_match"], ndigits=5) == 0.00849
    assert round(frugality_score[0, "mean_conso_per_token"], ndigits=6) == 0.000008
    assert len(frugality_score.columns) == 7
    frugality_score = calculate_frugality_score(data, n_match=None)
    assert len(frugality_score.columns) == 4
    assert "mean_conso_per_match" not in frugality_score.columns
    assert round(frugality_score[0, "mean_conso_per_token"], ndigits=6) == 0.000134
    assert round(frugality_score[0, "total_output_tokens"]) == 421
