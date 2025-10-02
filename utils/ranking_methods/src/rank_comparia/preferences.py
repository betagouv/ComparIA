import os
import operator
import polars as pl
from pathlib import Path
from rank_comparia.utils import load_comparia

POSITIVE_REACTIONS = [
    "useful",
    "creative",
    "complete",
    "clear_formatting",
]
NEGATIVE_REACTIONS = ["incorrect", "superficial", "instructions_not_followed"]


def get_votes_preferences():
    data = load_comparia("ministere-culture/comparia-votes")
    data = (
        pl.concat(
            [
                data.select(
                    model_name=pl.col("model_a_name"),
                    **{
                        **{reaction: f"conv_{reaction}_a" for reaction in POSITIVE_REACTIONS},
                        **{reaction: f"conv_{reaction}_a" for reaction in NEGATIVE_REACTIONS},
                    },
                ),
                data.select(
                    model_name=pl.col("model_b_name"),
                    **{
                        **{reaction: f"conv_{reaction}_b" for reaction in POSITIVE_REACTIONS},
                        **{reaction: f"conv_{reaction}_b" for reaction in NEGATIVE_REACTIONS},
                    },
                ),
            ]
        )
        .group_by("model_name")
        .sum()
        .sort(by="model_name")
        .drop_nulls()
    )
    data = data.with_columns(
        total_prefs=pl.fold(
            acc=pl.lit(0),
            function=operator.add,
            exprs=pl.col(*POSITIVE_REACTIONS, *NEGATIVE_REACTIONS),
        )
    )
    data = data.with_columns(
        positive_prefs_ratio=pl.fold(
            acc=pl.lit(0),
            function=operator.add,
            exprs=pl.col(*POSITIVE_REACTIONS),
        )
        / pl.col("total_prefs")
    )

    return data


if __name__ == "__main__":
    OUTPUT_PATH = Path(__file__).parent.parent.parent / "output"
    votes_preferences = get_votes_preferences()
    votes_preferences.write_json(Path("output") / "preferences-votes.json")
