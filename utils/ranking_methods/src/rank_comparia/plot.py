# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT
"""
Plot functions.
"""

from pathlib import Path
from typing import Literal

import altair as alt
import polars as pl


def plot_score_mean_win_proba(scores: pl.DataFrame) -> alt.Chart:
    """
    Plot ELO-type scores against mean probability to win against
    all other models.

    Args:
        scores (pl.DataFrame): Scores DataFrame with columns "model_name", "median".
    Returns:
        alt.Chart: Plot.
    """
    df = scores.select("model_name", "median")
    df_pairs = (
        df.join(df, how="cross", suffix="_opp")
        .filter(pl.col("model_name") != pl.col("model_name_opp"))
        .with_columns((1 / (1 + 10 ** ((pl.col("median_opp") - pl.col("median")) / 400))).alias("p_win"))
    )

    df_result = (
        df_pairs.group_by("model_name", "median")
        .agg(pl.mean("p_win").alias("mean_win_prob"))
        .sort("median", descending=True)
    )
    df_results = df_result.to_pandas()
    return (
        alt.Chart(df_result)
        .mark_circle(size=80)
        .encode(
            x=alt.X(
                "median:Q",
                title="Score",
                scale=alt.Scale(domain=[df_results["median"].min(), df_results["median"].max()]),  # type: ignore
            ),
            y=alt.Y(
                "mean_win_prob:Q",
                title="Mean win probability",
                scale=alt.Scale(
                    domain=[df_results["mean_win_prob"].min(), df_results["mean_win_prob"].max()]  # type: ignore
                ),
            ),
            tooltip=["model_name", "median", "mean_win_prob"],
        )
        .properties(width=500, height=400, title="Score vs. mean win probability")
    )


def plot_scores_with_confidence(scores: pl.DataFrame) -> alt.LayerChart:
    """
    Plot models scores.

    Args:
        scores (pl.DataFrame): Scores DataFrame with columns "model_name", "median", "p2.5" and "p97.5".
    Returns:
        alt.Chart: Plot.
    """
    scores = scores.sort("median", descending=True)
    model_order = scores["model_name"].to_list()
    df = scores.to_pandas()

    error_bars = (
        alt.Chart(df)
        .mark_errorbar(extent="ci", color="lightblue", thickness=4)
        .encode(
            x=alt.X("model_name:N", sort=model_order, title="Model"), y=alt.Y("p2.5:Q", title="Score"), y2="p97.5:Q"
        )
    )
    medians = (
        alt.Chart(df)
        .mark_point(color="black", thickness=1)
        .encode(x=alt.X("model_name:N", sort=model_order), y="median:Q")
    )

    # Combine
    return (error_bars + medians).properties(
        width=800,
        height=500,
    )


def format_matches_for_heatmap(matches: pl.DataFrame) -> pl.DataFrame:
    """
    From a DataFrame of matches with columns "score, "model_a" and "model_b"
    where score is 2 when B wins, 0 when A wins and 1 if draw,
    returned aggregated match data to plot in heatmaps..

    Args:
        matches (pl.DataFrame): Matches.
    Returns:
        pl.DataFrame: Heatmap.
    """
    df = matches.with_columns(
        a_wins=pl.when(pl.col("score") == 2).then(1).otherwise(0),
        b_wins=pl.when(pl.col("score") == 1).then(1).otherwise(0),
        draws=pl.when(pl.col("score") == 0).then(1).otherwise(0),
    ).select("model_a", "model_b", "a_wins", "b_wins", "draws")

    # count of wins by pair of model
    counts = df.group_by(["model_a", "model_b"]).agg(
        pl.col("a_wins").sum(), pl.col("b_wins").sum(), pl.col("draws").sum()
    )
    # reversed counts since we want to add match statistics of a vs. b and b vs. a
    reversed_counts = counts.select(
        model_a="model_b",
        model_b="model_a",
        a_wins="b_wins",
        b_wins="a_wins",
        draws="draws",
    )
    # aggregate counts
    return (
        (
            pl.concat([counts, reversed_counts])
            .group_by(["model_a", "model_b"])
            .agg(pl.sum("a_wins"), pl.sum("b_wins"), pl.sum("draws"))
        )
        .with_columns((pl.col("a_wins") + pl.col("b_wins") + pl.col("draws")).alias("count"))
        .with_columns((pl.col("a_wins") / (pl.col("a_wins") + pl.col("b_wins"))).round(2).alias("a_win_ratio"))
    )


def plot_match_counts(heatmap_data: pl.DataFrame) -> alt.LayerChart:
    """
    From aggregated data with columns "model_a", "model_b" and "count"
    plot a heatmap of match counts.

    Args:
        heatmap_data (pl.DataFrame): Matches data.
    Returns:
        alt.Chart: Heatmap.
    """
    # plot
    base = (
        alt.Chart(heatmap_data.to_pandas())
        .encode(
            x=alt.X("model_b:N", title="Modèle B", sort=alt.EncodingSortField(field="model_b", order="descending")),
            y=alt.Y("model_a:N", title="Modèle A", sort=alt.EncodingSortField(field="model_a")),
        )
        .properties(
            width=1000,
            height=1000,
        )
    )
    heatmap = base.mark_rect(opacity=0.7).encode(
        color=alt.Color("count:Q", scale=alt.Scale(scheme="viridis"), legend=None)
    )
    text = base.mark_text(color="black", fontSize=7).encode(text=alt.Text("count:Q"))

    final_chart = heatmap + text
    # rotate x-axis labels 45 degrees
    return final_chart.configure_axisX(labelAngle=45)


def plot_winrate_heatmap(heatmap_data: pl.DataFrame) -> alt.LayerChart:
    """
    From aggregated data with columns "model_a", "model_b" and "a_win_ratio",
    plot a heatmap of winrates by confrontation.

    Args:
        heatmap_data (pl.DataFrame): Matches data.
    Returns:
        alt.Chart: Heatmap.
    """
    # plot
    base = (
        alt.Chart(heatmap_data.to_pandas()[["model_a", "model_b", "a_win_ratio"]].dropna())  # type: ignore
        .encode(
            x=alt.X(
                "model_b:N", title="Modèle B: Perdant", sort=alt.EncodingSortField(field="model_b", order="descending")
            ),
            y=alt.Y("model_a:N", title="Modèle A: Gagnant", sort=alt.EncodingSortField(field="model_a")),
        )
        .properties(
            width=1000,
            height=1000,
        )
    )
    heatmap = base.mark_rect(opacity=0.7).encode(
        color=alt.Color("a_win_ratio:Q", scale=alt.Scale(scheme="redblue"), legend=None)
    )
    text = base.mark_text(color="black", fontSize=7).encode(text=alt.Text("a_win_ratio:Q"))

    final_chart = heatmap + text
    # rotate x-axis labels 45 degrees
    return final_chart.configure_axisX(labelAngle=45)


def plot_elo_against_frugal_elo(frugal_log_score: pl.DataFrame, bootstraped_scores: pl.DataFrame) -> alt.Chart:
    """
    Draw chart displaying Elo scores against Elo score adjusted for frugality.

    Args:
        frugal_log_score (pl.DataFrame): DataFrame with frugality score.
        bootstraped_scores (pl.DataFrame): DataFrame with bootstraped scores

    Returns:
        alt.Chart: chart displaying Elo scores against Elo score adjusted for frugality.
    """
    # Add infos about models (organization, license, etc)
    model_infos = pl.read_json(source=Path(".").resolve().parent / "data" / "models_data.json")
    all_data = (
        bootstraped_scores.select(["model_name", "median"])
        .join(frugal_log_score, on="model_name")
        .join(model_infos, on="model_name")
    )

    all_data_frugal = all_data.with_columns(frugal=(pl.col("median") - 366 * pl.col("cost")))
    max_frugal = all_data_frugal.max().item(0, "frugal") // 100 * 100 + 100
    min_frugal = all_data_frugal.min().item(0, "frugal") // 100 * 100
    max_elo = all_data_frugal.max().item(0, "median") // 100 * 100 + 100
    min_elo = all_data_frugal.min().item(0, "median") // 100 * 100

    # Construction of a slider to adjust how much we want to take into account frugality in scoring
    bind_range = alt.binding_range(min=0, max=1, name="frugality coefficient:  ")
    param_width = alt.param(bind=bind_range, value=1)

    x = alt.X("median").title("elo score").scale(type="linear").scale(domainMin=min_elo, domainMax=max_elo)
    y = alt.Y("y:Q").title("frugality elo score").scale(domainMin=min_frugal, domainMax=max_frugal)
    return (
        alt.Chart(all_data)
        .mark_point(filled=True)
        .encode(
            x=x, y=y, color=alt.Color("organization:N"), tooltip=["model_name", "organization", "license", "median"]
        )
        .add_params(
            param_width,
        )
        .transform_calculate(
            y=alt.datum.median - param_width * (alt.datum.cost * 366)
        )  # 366 is the difference of score for 90% winrate for ELO
        .properties(width=800, height=450, title="frugality elo ranking")
        .configure_legend(
            labelLimit=300,
        )
    )


def draw_frugality_chart(
    frugality_infos: pl.DataFrame,
    scale: Literal["match", "token"] | None,
    log: bool = False,
    title: str = "",
) -> alt.Chart:
    """
    Draw chart displaying Elo/BT scores against frugality scores.

    Args:
        frugality_infos (pl.DataFrame): DataFrame with frugality scores.
        title (str): Chart title.
        scale (Literal) : Select to plot mean_per_token or mean_per_match if mean=True
        log (bool): Whether or not to use a log scale.

    Returns:
        alt.Chart: Chart displaying Elo/BT scores against frugality scores.
    """

    # Add infos about models (organization, license, etc)
    model_infos = pl.read_json(source=Path(".").resolve().parent / "data" / "models_data.json")
    all_data = frugality_infos.join(model_infos, on="model_name")

    # Dropdown to select models by license (TODO: filter by proprietary/openweights/opensource)
    input_dropdown = alt.binding_select(
        options=list(all_data["license"].unique()),
        labels=[option for option in list(all_data["license"].unique())],
        name="License : ",
    )
    select_license = alt.selection_point(fields=["license"], bind=input_dropdown)

    # Allow to filter by value of the legend
    select_organization = alt.selection_point(fields=["organization"], bind="legend")

    x_column = "conso_all_conv"

    if scale == "match":
        x_column = "mean_conso_per_match"
    elif scale == "token":
        x_column = "mean_conso_per_token"

    frugal_chart = (
        alt.Chart(all_data, title=title)
        .mark_point(filled=True)
        .encode(
            alt.Y("median:Q").scale(zero=False).title("elo score"),
            alt.X(f"{x_column}:Q").scale(type="log" if log else "linear"),
            alt.Color("organization:N"),
            opacity=alt.when(select_organization).then(alt.value(1)).otherwise(alt.value(0.3)),
            tooltip=["model_name", "organization", "license", "median", f"{x_column}"],
        )
        .transform_filter(select_license)
        .properties(height=300, width=500)
        .add_params(select_organization, select_license)
    )

    return frugal_chart
