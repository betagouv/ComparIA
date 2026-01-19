"""
Compute model rankings from comparia-votes and comparia-reactions datasets.
Replaces the external ranking_methods repository.
"""

import json
from datetime import datetime
from pathlib import Path

import polars as pl
from datasets import load_dataset
from arena_rank.models.bradley_terry import BradleyTerry
from arena_rank.utils.data_utils import PairDataset

OUTPUT_PATH = Path(__file__).parent.parent / "models" / "generated-models-extra-data.json"

# Preference columns in comparia-votes
POSITIVE_PREFS = ["useful", "creative", "complete", "clear_formatting"]
NEGATIVE_PREFS = ["incorrect", "superficial", "instructions_not_followed"]


def fetch_votes() -> pl.DataFrame:
    """Fetch comparia-votes from HuggingFace."""
    print("Fetching comparia-votes from HuggingFace...")
    ds = load_dataset("ministere-culture/comparia-votes", split="train")
    df = pl.from_arrow(ds.data.table)
    print(f"  {len(df)} votes loaded")
    return df


def fetch_reactions() -> pl.DataFrame:
    """Fetch comparia-reactions from HuggingFace."""
    print("Fetching comparia-reactions from HuggingFace...")
    ds = load_dataset("ministere-culture/comparia-reactions", split="train")
    df = pl.from_arrow(ds.data.table)
    print(f"  {len(df)} reactions loaded")
    return df


def get_battles_from_votes(votes: pl.DataFrame) -> pl.DataFrame:
    """Extract battles with clear winners from votes."""
    battles = votes.filter(
        (pl.col("both_equal") == False) &
        (pl.col("chosen_model_name").is_not_null())
    )

    return battles.select([
        pl.col("model_a_name").alias("model_a"),
        pl.col("model_b_name").alias("model_b"),
        pl.when(pl.col("chosen_model_name") == pl.col("model_a_name"))
          .then(pl.lit("model_a"))
          .otherwise(pl.lit("model_b"))
          .alias("winner")
    ])


def get_battles_from_reactions(reactions: pl.DataFrame) -> pl.DataFrame:
    """
    Convert reactions to battles.
    A 'liked' reaction for a model = vote for that model.
    A 'disliked' reaction for a model = vote for the opponent.
    """
    # Filter to reactions with a clear signal
    with_signal = reactions.filter(
        (pl.col("liked") == True) | (pl.col("disliked") == True)
    )

    # Determine winner based on reaction
    # If model is liked -> that model wins
    # If model is disliked -> opponent wins
    return with_signal.select([
        pl.col("model_a_name").alias("model_a"),
        pl.col("model_b_name").alias("model_b"),
        pl.when(
            (pl.col("liked") == True) & (pl.col("refers_to_model") == pl.col("model_a_name"))
        ).then(pl.lit("model_a"))
        .when(
            (pl.col("liked") == True) & (pl.col("refers_to_model") == pl.col("model_b_name"))
        ).then(pl.lit("model_b"))
        .when(
            (pl.col("disliked") == True) & (pl.col("refers_to_model") == pl.col("model_a_name"))
        ).then(pl.lit("model_b"))  # Dislike A = vote for B
        .when(
            (pl.col("disliked") == True) & (pl.col("refers_to_model") == pl.col("model_b_name"))
        ).then(pl.lit("model_a"))  # Dislike B = vote for A
        .otherwise(pl.lit(None))
        .alias("winner")
    ]).filter(pl.col("winner").is_not_null())


def compute_rankings(votes: pl.DataFrame, reactions: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Compute Bradley-Terry rankings using arena-rank from votes + reactions."""
    print("Computing Bradley-Terry rankings...")

    # Get battles from both sources
    vote_battles = get_battles_from_votes(votes)
    reaction_battles = get_battles_from_reactions(reactions)

    print(f"  {len(vote_battles)} battles from votes")
    print(f"  {len(reaction_battles)} battles from reactions")

    # Combine all battles
    all_battles = pl.concat([vote_battles, reaction_battles])
    print(f"  {len(all_battles)} total battles")

    # Convert to pandas for arena-rank
    pairs_pd = all_battles.to_pandas()

    # Create PairDataset
    dataset = PairDataset.from_pandas(
        pairs_pd,
        competitor_cols=["model_a", "model_b"],
        outcome_col="winner",
        min_pair_count=1  # Include all models
    )

    print(f"  {dataset.n_competitors} unique models")

    # Compute ratings
    model = BradleyTerry(n_competitors=dataset.n_competitors)
    results = model.compute_ratings_and_cis(dataset, significance_level=0.05)

    # Build results DataFrame
    rankings = pl.DataFrame({
        "model_name": results["competitors"],
        "median": [float(r) for r in results["ratings"]],
        "p2.5": [float(r) for r in results["rating_lower"]],
        "p97.5": [float(r) for r in results["rating_upper"]],
    }).sort("median", descending=True)

    # Add ranks
    rankings = rankings.with_row_index("rank", offset=1)

    # Compute rank bounds from CI overlaps
    rankings = compute_rank_bounds(rankings)

    return rankings, all_battles


def compute_rank_bounds(df: pl.DataFrame) -> pl.DataFrame:
    """Compute rank confidence bounds based on CI overlaps."""
    print("Computing rank confidence bounds...")

    records = df.to_dicts()
    n = len(records)

    for i, row in enumerate(records):
        upper_ci = row["p97.5"]
        lower_ci = row["p2.5"]

        # Best rank: 1 + count of models whose lower CI > our upper CI
        best = 1 + sum(1 for r in records if r["p2.5"] > upper_ci)

        # Worst rank: count of models whose upper CI > our lower CI
        worst = sum(1 for r in records if r["p97.5"] > lower_ci)

        records[i]["rank_p2.5"] = best
        records[i]["rank_p97.5"] = min(worst, n)

    return pl.DataFrame(records)


def compute_match_counts(votes: pl.DataFrame, reactions: pl.DataFrame) -> pl.DataFrame:
    """Count matches per model from votes and reactions."""
    print("Computing match counts...")

    # Votes counts
    va_counts = votes.group_by("model_a_name").agg(pl.len().alias("n")).rename({"model_a_name": "model_name"})
    vb_counts = votes.group_by("model_b_name").agg(pl.len().alias("n")).rename({"model_b_name": "model_name"})

    # Reactions counts (only those with a signal)
    reactions_with_signal = reactions.filter(
        (pl.col("liked") == True) | (pl.col("disliked") == True)
    )
    ra_counts = reactions_with_signal.group_by("model_a_name").agg(pl.len().alias("n")).rename({"model_a_name": "model_name"})
    rb_counts = reactions_with_signal.group_by("model_b_name").agg(pl.len().alias("n")).rename({"model_b_name": "model_name"})

    return pl.concat([va_counts, vb_counts, ra_counts, rb_counts]).group_by("model_name").agg(
        pl.col("n").sum().alias("n_match")
    )


def compute_win_rates(battles: pl.DataFrame) -> pl.DataFrame:
    """Compute classic win rate for each model."""
    print("Computing win rates...")

    # Count wins for each model
    wins_a = battles.filter(pl.col("winner") == "model_a").group_by("model_a").agg(
        pl.len().alias("wins")
    ).rename({"model_a": "model_name"})

    wins_b = battles.filter(pl.col("winner") == "model_b").group_by("model_b").agg(
        pl.len().alias("wins")
    ).rename({"model_b": "model_name"})

    total_wins = pl.concat([wins_a, wins_b]).group_by("model_name").agg(
        pl.col("wins").sum()
    )

    # Count total battles per model
    battles_a = battles.group_by("model_a").agg(pl.len().alias("total")).rename({"model_a": "model_name"})
    battles_b = battles.group_by("model_b").agg(pl.len().alias("total")).rename({"model_b": "model_name"})

    total_battles = pl.concat([battles_a, battles_b]).group_by("model_name").agg(
        pl.col("total").sum()
    )

    # Join and compute win rate
    result = total_wins.join(total_battles, on="model_name", how="outer_coalesce")
    result = result.fill_null(0)
    result = result.with_columns(
        (pl.col("wins") / pl.col("total")).alias("win_rate")
    ).select(["model_name", "win_rate"])

    return result


def compute_mean_win_prob(rankings: pl.DataFrame) -> pl.DataFrame:
    """
    Compute mean win probability for each model based on Bradley-Terry scores.
    P(i beats j) = score_i / (score_i + score_j)
    mean_win_prob = average of this across all opponents
    """
    print("Computing mean win probabilities...")

    records = rankings.to_dicts()
    scores = {r["model_name"]: r["median"] for r in records}
    model_names = list(scores.keys())

    result = []
    for model in model_names:
        my_score = scores[model]
        probs = []
        for opponent in model_names:
            if opponent != model:
                opp_score = scores[opponent]
                # Bradley-Terry probability
                prob = my_score / (my_score + opp_score)
                probs.append(prob)
        mean_prob = sum(probs) / len(probs) if probs else 0.0
        result.append({"model_name": model, "mean_win_prob": mean_prob})

    return pl.DataFrame(result)


def compute_preferences(votes: pl.DataFrame) -> pl.DataFrame:
    """Aggregate preference counts per model."""
    print("Computing preferences...")

    pref_cols = POSITIVE_PREFS + NEGATIVE_PREFS

    # Model A preferences
    a_prefs = votes.select([
        pl.col("model_a_name").alias("model_name"),
        *[pl.col(f"conv_{p}_a").fill_null(False).cast(pl.Int64).alias(p) for p in pref_cols]
    ])

    # Model B preferences
    b_prefs = votes.select([
        pl.col("model_b_name").alias("model_name"),
        *[pl.col(f"conv_{p}_b").fill_null(False).cast(pl.Int64).alias(p) for p in pref_cols]
    ])

    # Combine and aggregate
    all_prefs = pl.concat([a_prefs, b_prefs])

    result = all_prefs.group_by("model_name").agg([
        pl.col(p).sum().alias(p) for p in pref_cols
    ])

    # Compute totals and ratio
    pos_cols = [pl.col(p) for p in POSITIVE_PREFS]
    neg_cols = [pl.col(p) for p in NEGATIVE_PREFS]
    all_cols = pos_cols + neg_cols

    result = result.with_columns([
        pl.sum_horizontal(all_cols).alias("total_prefs"),
    ])

    result = result.with_columns([
        pl.when(pl.col("total_prefs") > 0)
          .then(pl.sum_horizontal(pos_cols) / pl.col("total_prefs"))
          .otherwise(pl.lit(None))
          .alias("positive_prefs_ratio")
    ])

    return result


def main():
    votes = fetch_votes()
    reactions = fetch_reactions()

    rankings, all_battles = compute_rankings(votes, reactions)
    match_counts = compute_match_counts(votes, reactions)
    preferences = compute_preferences(votes)
    win_rates = compute_win_rates(all_battles)
    mean_win_probs = compute_mean_win_prob(rankings)

    # Join all data
    print("Joining data...")
    result = rankings.join(match_counts, on="model_name", how="left")
    result = result.join(preferences, on="model_name", how="left")
    result = result.join(win_rates, on="model_name", how="left")
    result = result.join(mean_win_probs, on="model_name", how="left")

    # Fill nulls
    result = result.fill_null(0)

    # Format output
    output = {
        "timestamp": datetime.now().timestamp(),
        "models": result.to_dicts()
    }

    print(f"Writing to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Done. {len(result)} models ranked.")


if __name__ == "__main__":
    main()
