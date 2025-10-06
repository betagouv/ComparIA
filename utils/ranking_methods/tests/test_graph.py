# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

import polars as pl
import pytest

from rank_comparia.utils_graph_d3 import get_df_source_sink_timestamp


@pytest.fixture(name="data")
def fixture_data():
    return pl.read_parquet("tests/data/sample_comparia_votes.parquet")


def test_get_df_source_sink_timestamp(data):
    source_timestamp = get_df_source_sink_timestamp(data, None)
    assert len(source_timestamp.columns) == 8
    assert "sink_node_model_winner" in source_timestamp.columns
    assert "source_node_model_loser" in source_timestamp.columns
    assert "timestamp_iso" in source_timestamp.columns
    source_timestamp_2025 = get_df_source_sink_timestamp(data, 2025)
    assert 2024 not in source_timestamp_2025["year"].to_list()
    source_timestamp_2024 = get_df_source_sink_timestamp(data, 2024)
    assert 2025 not in source_timestamp_2024["year"].to_list()
