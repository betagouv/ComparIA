# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

import json
from typing import Literal

import networkx as nx
import polars as pl
from networkx.readwrite import json_graph


def get_df_source_sink_timestamp(df: pl.DataFrame, year: Literal[2024, 2025] | None) -> pl.DataFrame:
    """
    Restructures the data in order to have sink (a model who won a match) and
    source (a model who lost a match) nodes to plot
    a dynamic graph.

    Args:
        df (pl.DataFrame): Votes DataFrame with columns "id", "timestamp",
        "model_a_name", "model_b_name", "chosen_model_name".
        year (str): 2024, 2025 or None to filter data.
    Returns:
        df: pl.DataFrame with two new columns  "sink_node_model_winner",
        "source_node_model_loser".
    """
    if "chosen_model_name" in df.columns:
        df = df.filter(pl.col("chosen_model_name") != "null")

    df = df.select(
        [
            "id",
            "timestamp",
            "model_a_name",
            "model_b_name",
            "chosen_model_name",
        ]
    ).sort("timestamp")
    df = df.with_columns(
        pl.when(pl.col("chosen_model_name") == pl.col("model_a_name"))
        .then(pl.col("model_a_name"))
        .otherwise(pl.col("model_b_name"))
        .alias("sink_node_model_winner")
    )
    df = df.with_columns(
        pl.when(pl.col("chosen_model_name") == pl.col("model_b_name"))
        .then(pl.col("model_a_name"))
        .otherwise(pl.col("model_b_name"))
        .alias("source_node_model_loser")
    )

    df = df.filter(pl.col("model_a_name") != pl.col("model_b_name"))

    df = df.select(["id", "timestamp", "sink_node_model_winner", "source_node_model_loser"]).sort("timestamp")

    # add timestamp iso because datetime not read in js
    df = df.with_columns(
        pl.col("timestamp").dt.convert_time_zone("UTC").dt.to_string("%Y-%m-%dT%H:%M:%SZ").alias("timestamp_iso")
    )

    df = df.with_columns(
        pl.col("timestamp").dt.month().alias("month"),
        pl.col("timestamp").dt.day().alias("day"),
        pl.col("timestamp").dt.year().alias("year"),
    )

    if year:
        df = df.filter(pl.col("year") == year)

    return df


def create_graph(df: pl.DataFrame, var_1_source: str, var_2_sink: str) -> nx.Graph:
    """
    Creates a graph, where the models in ComparIA are nodes and a link from
    model A to model B means that model A won a match (received a vote from
    a user) against model B.

    Args:
        df (pl.DataFrame): Votes DataFrame with columns "id", "timestamp",
        "sink_node_model_winner","source_node_model_loser", "month", "day", "year".
        var_1_source (str): column name with source node.
        var_2_sink (str): column name with sink node.
    Returns:
        G: Networkx graph object. Nodes and links have attributes: start_date
        (timestamp of the match) and end_date (max of timestamps).
    """
    unique_model_a = df[var_2_sink].unique().to_list()
    unique_model_b = df[var_1_source].unique().to_list()
    all_models = list(set(unique_model_a + unique_model_b))
    end_date = df["timestamp_iso"].max()
    G = nx.DiGraph()
    editors = pl.read_json("../data/models_data_augmented.json")

    for model in all_models:
        source_timestamps = df.filter(pl.col(var_1_source) == model).select(pl.col("timestamp_iso"))
        a = source_timestamps.min().item() if not source_timestamps.is_empty() else None
        b = source_timestamps.max().item() if not source_timestamps.is_empty() else None
        if model in editors["model_name"].unique().to_list():
            editor = editors.filter(pl.col("model_name") == model)["organization"].item()

        G.add_node(model, start_date=min(a, b), end_date=end_date, model=model, editor=editor)  # type: ignore

    edges_to_add = []
    for row in df.iter_rows(named=True):
        loser = row[var_1_source]
        winner = row[var_2_sink]
        rencontre_timestamp_str = row["timestamp_iso"]

        edge_start_date = rencontre_timestamp_str
        edge_end_date = end_date

        edge_date = {
            "start_date": edge_start_date,
            "end_date": edge_end_date,
        }
        edges_to_add.append((loser, winner, edge_date))

    G.add_edges_from(edges_to_add)

    return G


def create_graph_json(df: pl.DataFrame, title: str, var1: str, var2: str):
    """
    Saves a networkx graph object into a json file.

    Args:
        df (pl.DataFrame): Votes DataFrame with columns "id", "timestamp",
        "sink_node_model_winner","source_node_model_loser", "month", "day", "year".
        title (str): name of the json file.
        var1 (str): column name with source node.
        var2 (str): column name with sink node.
    Returns:
        json file with nodes and edges.
    """
    G = create_graph(df=df, var_1_source=var1, var_2_sink=var2)

    rencontres_comparIA_graph = json_graph.node_link_data(G)

    with open("../data/" + title, "w", encoding="utf-8") as f:
        json.dump(rencontres_comparIA_graph, f, ensure_ascii=False, indent=4)
