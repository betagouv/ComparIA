# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT
"""
Legacy functions for data transformation.
"""

import polars as pl


POSITIVE_COLUMNS = ["liked", "useful", "creative", "clear_formatting"]
NEGATIVE_COLUMNS = ["disliked", "incorrect", "superficial", "instructions_not_followed"]


def get_matches_with_score(reactions: pl.DataFrame) -> pl.DataFrame:
    """
    Compute a 'reactions score' (number of positive reactions - number
    of negative reactions) per model for each match in the reactions data.

    Args:
        reactions (pl.DataFrame): Reactions data.

    Returns:
        pl.DataFrame: A DataFrame with the reactions score for each match.
    """
    comparia_reactions = reactions.sort("timestamp").with_columns(
        *[pl.col(bool_to_zero).fill_null(value=False).cast(int) for bool_to_zero in POSITIVE_COLUMNS + NEGATIVE_COLUMNS]
    )
    likability_score = pl.sum_horizontal(*POSITIVE_COLUMNS) - pl.sum_horizontal(*NEGATIVE_COLUMNS)
    return (
        comparia_reactions.with_columns(
            score_a=pl.when(model_pos="a").then(likability_score).otherwise(0),
            score_b=pl.when(model_pos="b").then(likability_score).otherwise(0),
        )["model_a_name", "model_b_name", "score_a", "score_b", "conversation_pair_id"]
        .group_by(["model_a_name", "model_b_name", "conversation_pair_id"])
        .sum()
    )


def get_winners(matches: pl.DataFrame) -> pl.DataFrame:
    """
    Get winner model for each match in the reactions data.

    Args:
        matches (pl.DataFrame): Match data with model scores coming from the reactions data.

    Returns:
        pl.DataFrame: A DataFrame with the winner model for each match.
    """
    return matches.with_columns(
        model_name=pl.when(pl.col("score_a") > pl.col("score_b"))
        .then(pl.col("model_a_name"))
        .when(pl.col("score_a") < pl.col("score_b"))
        .then(pl.col("model_b_name"))
        .otherwise(None)
    ).filter(pl.col("model_name").is_not_null())


def get_winrates(winners: pl.DataFrame) -> pl.DataFrame:
    """
    Compute winrate per model from a DataFrame with the winning model for
    each match.

    Args:
        winners (pl.DataFrame): DataFrame with match winners.

    Returns:
        pl.DataFrame: Winrates DataFrame.
    """
    winners_len = winners.group_by("model_name").len().with_columns(wins=pl.col("len")).drop("len")
    all_matches = (
        pl.concat(
            [
                winners.group_by("model_a_name")
                .len()
                .with_columns(model_name=pl.col("model_a_name"))
                .drop("model_a_name"),
                winners.group_by("model_b_name")
                .len()
                .with_columns(model_name=pl.col("model_b_name"))
                .drop("model_b_name"),
            ]
        )
        .group_by("model_name")
        .sum()
        .sort("len", descending=True)
    )
    return (
        all_matches.join(winners_len, on="model_name")
        .with_columns(winrate=100 * pl.col("wins") / pl.col("len"))
        .sort("len", descending=True)
    )
