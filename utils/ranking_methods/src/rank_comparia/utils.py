# SPDX-FileCopyrightText: 2025 Pôle d'Expertise de la Régulation Numérique <contact@peren.gouv.fr>
#
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Literal

import datasets
import polars as pl


def save_data(data: pl.DataFrame, title: str, save_path: Path) -> None:
    """
    Save polars DataFrame as a csv file.

    Args:
        data (pl.DataFrame): DataFrame with all infos calculated.
        title (str): File name.
        save_path (Path): Repository.
    """
    data.write_csv(file=save_path / f"{title}.csv", separator=";")


def load_comparia(
    repository: Literal[
        "ministere-culture/comparia-reactions",
        "ministere-culture/comparia-votes",
    ],
    **kwargs,
) -> pl.DataFrame:
    """
    Load `comparia-reactions` or `comparia-votes` as a polars DataFrame
    with a category field coming from `comparia-conversations`.
    Extra keyword arguments will be forwarded to `datasets.load_dataset`.

    Args:
        repository (Literal[
            "ministere-culture/comparia-reactions",
            "ministere-culture/comparia-votes",
        ]): HF repository name.

    Returns:
        pl.DataFrame: Dataset.
    """
    # environment variable HF_HOME must be set
    # and authentication to the hub is necessary
    data: pl.DataFrame = datasets.load_dataset(
        repository,
        split="train",
        **kwargs,
    ).to_polars()  # type: ignore

    # add categories column
    conversations: pl.DataFrame = datasets.load_dataset(
        "ministere-culture/comparia-conversations", split="train", **kwargs
    ).to_polars()  # type: ignore
    conversations = conversations.select(
        [
            "conversation_pair_id",
            "categories",
            "model_a_active_params",
            "total_conv_a_output_tokens",
            "total_conv_a_kwh",
            "model_b_active_params",
            "total_conv_b_output_tokens",
            "total_conv_b_kwh",
        ]
    )
    data = data.join(conversations, on="conversation_pair_id")

    return data


# List of categories in the `comparia-conversation` dataset (column "categories")
categories: list[str] = [
    "Education",
    "Arts",
    "Entertainment & Travel & Hobby",
    "Culture & Cultural geography",
    "Politics & Government",
    "Food & Drink & Cooking",
    "Law & Justice",
    "Natural Science & Formal Science & Technology",
    "Business & Economics & Finance",
    "Society & Social Issues & Human Rights",
    "Other",
    "Personal Development & Human Resources & Career",
    "Environment",
    "Health & Wellness & Medicine",
    "Shopping & Commodity",
    "Daily Life & Home & Lifestyle",
    "Religion & Spirituality",
    "Sports",
    "History",
    "Real Estate",
    "Philosophy",
    "International",
    "Psychology",
    "Security",
    "Philosophy & Spirituality",
    "Fashion",
    "Music",
    "Marketing",
    "Ethics & Debate",
    "Philosophy & logic",
    "Philosophy & Ethics",
    "Industry",
    "Robotics",
    "Travel",
    "Technology",
    "Travel & Hobby",
    "Philosophy and Ethics",
    "Theology",
    "Anthropology",
    "Philosophy & Religion",
    "Urban Planning",
    "Agriculture",
    "Linguistics",
    "Philosophy & Metaphysics",
    "Psychology & Mental Health",
    "Sociology",
    "Architecture and construction",
    "Industry and artisanat",
    "Biotechnology",
    "Marketing & Sales",
    "Mathematics",
    "Engineering",
    "Ethics",
]
