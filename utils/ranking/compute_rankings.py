"""
Compute model rankings from comparia-votes and comparia-reactions datasets.
Replaces the external ranking_methods repository.

Includes both standard Bradley-Terry rankings and style-controlled rankings
that adjust for user preferences toward longer, better-formatted responses.
"""

import json
import math
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl
from datasets import load_dataset
from sklearn.linear_model import LogisticRegression
from tqdm import tqdm
from arena_rank.models.bradley_terry import BradleyTerry
from arena_rank.utils.data_utils import PairDataset

OUTPUT_PATH = Path(__file__).parent.parent / "models" / "generated-models-extra-data.json"

# Preference columns in comparia-votes
POSITIVE_PREFS = ["useful", "creative", "complete", "clear_formatting"]
NEGATIVE_PREFS = ["incorrect", "superficial", "instructions_not_followed"]

# Style control settings
STYLE_FEATURES = ["tokens", "headers", "lists", "bold"]
BOOTSTRAP_SAMPLES = 100  # Number of bootstrap iterations for confidence intervals
BT_SCALE = 400  # Bradley-Terry scale factor
BT_BASE = 10  # Bradley-Terry base
BT_INIT_RATING = 1000  # Initial rating

# Model name aliases - maps alternative names to canonical names
# Used to merge votes/battles for models that appear under multiple names
MODEL_ALIASES = {
    "mistral-medium-3.1": "mistral-medium-2508",
    # Add more aliases here as needed
}


def normalize_model_name(name: str) -> str:
    """Normalize model name using aliases."""
    return MODEL_ALIASES.get(name, name)


# =============================================================================
# Style Feature Extraction Functions
# =============================================================================

def count_markdown_headers(text: str) -> int:
    """Count markdown headers (h1-h6)."""
    if not text:
        return 0
    total = 0
    for i in range(1, 7):
        pattern = rf'^{"#" * i}(?!#)\s'
        total += len(re.findall(pattern, text, re.MULTILINE))
    return total


def count_markdown_lists(text: str) -> int:
    """Count markdown list items (ordered + unordered)."""
    if not text:
        return 0
    ordered = len(re.findall(r'^\s*\d+\.\s+\S', text, re.MULTILINE))
    unordered = len(re.findall(r'^\s*[-*+]\s+\S', text, re.MULTILINE))
    return ordered + unordered


def count_markdown_bold(text: str) -> int:
    """Count bold text markers (**text** or __text__)."""
    if not text:
        return 0
    double_asterisk = len(re.findall(r'\*\*[^*]+\*\*', text))
    double_underscore = len(re.findall(r'__[^_]+__', text))
    return double_asterisk + double_underscore


def extract_assistant_text(conversation: list) -> str:
    """Extract all assistant response text from a conversation."""
    if not conversation:
        return ""
    parts = []
    for msg in conversation:
        if isinstance(msg, dict) and msg.get('role') == 'assistant' and msg.get('content'):
            parts.append(msg['content'])
    return '\n'.join(parts)


def extract_style_features(text: str) -> dict:
    """Extract all style features from text."""
    if not text:
        return {'tokens': 0, 'headers': 0, 'lists': 0, 'bold': 0}
    return {
        'tokens': len(text.split()),
        'headers': count_markdown_headers(text),
        'lists': count_markdown_lists(text),
        'bold': count_markdown_bold(text)
    }


def fetch_votes() -> pl.DataFrame:
    """Fetch comparia-votes from HuggingFace."""
    print("Fetching comparia-votes from HuggingFace...")
    ds = load_dataset("ministere-culture/comparia-votes", split="train")
    df = pl.from_arrow(ds.data.table)

    # Normalize model names using aliases
    df = df.with_columns([
        pl.col("model_a_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("model_a_name"),
        pl.col("model_b_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("model_b_name"),
        pl.col("chosen_model_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("chosen_model_name"),
    ])

    print(f"  {len(df)} votes loaded")
    return df


def fetch_reactions() -> pl.DataFrame:
    """Fetch comparia-reactions from HuggingFace."""
    print("Fetching comparia-reactions from HuggingFace...")
    ds = load_dataset("ministere-culture/comparia-reactions", split="train")
    df = pl.from_arrow(ds.data.table)

    # Normalize model names using aliases
    df = df.with_columns([
        pl.col("model_a_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("model_a_name"),
        pl.col("model_b_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("model_b_name"),
        pl.col("refers_to_model").map_elements(normalize_model_name, return_dtype=pl.String).alias("refers_to_model"),
    ])

    print(f"  {len(df)} reactions loaded")
    return df


def fetch_conversations() -> pl.DataFrame:
    """Fetch comparia-conversations for style feature extraction."""
    print("Fetching comparia-conversations from HuggingFace...")
    ds = load_dataset("ministere-culture/comparia-conversations", split="train")
    df = pl.from_arrow(ds.data.table)

    # Normalize model names using aliases
    df = df.with_columns([
        pl.col("model_a_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("model_a_name"),
        pl.col("model_b_name").map_elements(normalize_model_name, return_dtype=pl.String).alias("model_b_name"),
    ])

    print(f"  {len(df)} conversations loaded")
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


# =============================================================================
# Style-Controlled Bradley-Terry Functions
# =============================================================================

def prepare_style_battles(votes: pl.DataFrame, reactions: pl.DataFrame, conversations: pl.DataFrame) -> pl.DataFrame:
    """
    Prepare battles with style features for style-controlled ranking.
    Joins votes and reactions with conversations to extract style features from response text.
    """
    print("Preparing style battles...")

    # Get battles from votes
    vote_battles = votes.filter(
        (pl.col("both_equal") == False) &
        (pl.col("chosen_model_name").is_not_null())
    ).select([
        "conversation_pair_id",
        pl.col("model_a_name").alias("model_a"),
        pl.col("model_b_name").alias("model_b"),
        pl.col("chosen_model_name")
    ])

    # Get battles from reactions
    reaction_battles = reactions.filter(
        (pl.col("liked") == True) | (pl.col("disliked") == True)
    ).select([
        "conversation_pair_id",
        pl.col("model_a_name").alias("model_a"),
        pl.col("model_b_name").alias("model_b"),
        pl.when(
            (pl.col("liked") == True) & (pl.col("refers_to_model") == pl.col("model_a_name"))
        ).then(pl.col("model_a_name"))
        .when(
            (pl.col("liked") == True) & (pl.col("refers_to_model") == pl.col("model_b_name"))
        ).then(pl.col("model_b_name"))
        .when(
            (pl.col("disliked") == True) & (pl.col("refers_to_model") == pl.col("model_a_name"))
        ).then(pl.col("model_b_name"))  # Dislike A = vote for B
        .when(
            (pl.col("disliked") == True) & (pl.col("refers_to_model") == pl.col("model_b_name"))
        ).then(pl.col("model_a_name"))  # Dislike B = vote for A
        .otherwise(pl.lit(None))
        .alias("chosen_model_name")
    ]).filter(pl.col("chosen_model_name").is_not_null())

    # Combine all battles
    all_battles = pl.concat([vote_battles, reaction_battles])

    print(f"  {len(vote_battles)} battles from votes")
    print(f"  {len(reaction_battles)} battles from reactions")

    # Join with conversations to get conversation text
    # Only battles with matching conversation_pair_id will be included
    battles_with_conv = all_battles.join(
        conversations.select([
            "conversation_pair_id",
            "conversation_a",
            "conversation_b"
        ]),
        on="conversation_pair_id",
        how="inner"
    )

    print(f"  {len(battles_with_conv)} battles with conversation data (from votes + reactions)")

    # Extract style features
    records = []
    for row in tqdm(battles_with_conv.iter_rows(named=True), total=len(battles_with_conv), desc="Extracting style features"):
        conv_a = row["conversation_a"]
        conv_b = row["conversation_b"]

        # Handle potential string JSON
        if isinstance(conv_a, str):
            try:
                conv_a = json.loads(conv_a)
            except:
                conv_a = []
        if isinstance(conv_b, str):
            try:
                conv_b = json.loads(conv_b)
            except:
                conv_b = []

        text_a = extract_assistant_text(conv_a)
        text_b = extract_assistant_text(conv_b)

        features_a = extract_style_features(text_a)
        features_b = extract_style_features(text_b)

        # Determine winner
        winner = "model_a" if row["chosen_model_name"] == row["model_a"] else "model_b"

        records.append({
            "model_a": row["model_a"],
            "model_b": row["model_b"],
            "winner": winner,
            **{f"{k}_a": v for k, v in features_a.items()},
            **{f"{k}_b": v for k, v in features_b.items()}
        })

    return pl.DataFrame(records)


def fit_style_controlled_bt(
    battles: pl.DataFrame,
    models: list[str]
) -> tuple[dict[str, float], np.ndarray]:
    """
    Fit style-controlled Bradley-Terry model using logistic regression.

    The design matrix has:
    - Model indicator columns (one per model, +log(BASE) for model_a, -log(BASE) for model_b)
    - Style covariate columns (normalized style differences)

    Returns:
        Tuple of (model_ratings dict, style_coefficients array)
    """
    model_to_idx = {m: i for i, m in enumerate(models)}
    p = len(models)
    k = len(STYLE_FEATURES)

    # Duplicate battles (like notebook's pd.concat([df, df]))
    battles_list = battles.to_dicts()
    battles_list_dup = battles_list + battles_list
    n = len(battles_list_dup)

    # Build design matrix
    X = np.zeros((n, p + k))
    Y = np.zeros(n)

    # Style feature arrays for normalization
    style_diffs = {feat: [] for feat in STYLE_FEATURES}

    for i, row in enumerate(battles_list_dup):
        # Model positions
        idx_a = model_to_idx[row["model_a"]]
        idx_b = model_to_idx[row["model_b"]]

        X[i, idx_a] = math.log(BT_BASE)
        X[i, idx_b] = -math.log(BT_BASE)

        # Outcome
        Y[i] = 1.0 if row["winner"] == "model_a" else 0.0

        # Compute style differences
        for feat in STYLE_FEATURES:
            val_a = row[f"{feat}_a"]
            val_b = row[f"{feat}_b"]
            total = val_a + val_b + 1  # Add 1 to avoid division by zero
            diff = (val_a - val_b) / total
            style_diffs[feat].append(diff)

    # Normalize style features and add to design matrix
    for j, feat in enumerate(STYLE_FEATURES):
        arr = np.array(style_diffs[feat])
        mean = np.mean(arr)
        std = np.std(arr)
        if std == 0:
            std = 1
        normalized = (arr - mean) / std
        X[:, p + j] = normalized

    # Fit logistic regression
    lr = LogisticRegression(fit_intercept=False, max_iter=1000)
    lr.fit(X, Y)

    # Extract ratings
    coefficients = lr.coef_[0]
    model_scores = coefficients[:p]
    style_coefs = coefficients[p:]

    # Normalize model scores to have mean 0 (for identifiability in Bradley-Terry)
    # This ensures scores are centered around BT_INIT_RATING like standard rankings
    model_scores_normalized = model_scores - np.mean(model_scores)

    # Convert to rating scale
    ratings = {
        model: BT_SCALE * model_scores_normalized[i] + BT_INIT_RATING
        for model, i in model_to_idx.items()
    }

    return ratings, style_coefs


def compute_style_controlled_rankings(
    votes: pl.DataFrame,
    reactions: pl.DataFrame,
    conversations: pl.DataFrame
) -> pl.DataFrame:
    """
    Compute style-controlled Bradley-Terry rankings with bootstrap confidence intervals.
    Uses both votes and reactions (where conversation data is available).

    Returns DataFrame with columns: model_name, median, p2.5, p97.5, rank, rank_p2.5, rank_p97.5
    """
    print("Computing style-controlled rankings...")

    # Prepare battles with style features
    battles = prepare_style_battles(votes, reactions, conversations)

    if len(battles) == 0:
        print("  No battles with style features found!")
        return pl.DataFrame()

    # Get unique models
    models = sorted(set(battles["model_a"].to_list() + battles["model_b"].to_list()))
    print(f"  {len(models)} unique models, {len(battles)} battles")

    # Fit on full data for point estimates
    ratings, style_coefs = fit_style_controlled_bt(battles, models)

    print(f"  Style coefficients: tokens={style_coefs[0]:.4f}, headers={style_coefs[1]:.4f}, "
          f"lists={style_coefs[2]:.4f}, bold={style_coefs[3]:.4f}")

    # Bootstrap for confidence intervals
    print(f"  Running {BOOTSTRAP_SAMPLES} bootstrap samples for confidence intervals...")
    bootstrap_ratings = {model: [] for model in models}

    battles_list = battles.to_dicts()
    n_battles = len(battles_list)

    for _ in tqdm(range(BOOTSTRAP_SAMPLES), desc="Bootstrap"):
        # Sample with replacement
        indices = np.random.choice(n_battles, size=n_battles, replace=True)
        sample_battles = pl.DataFrame([battles_list[i] for i in indices])

        try:
            sample_ratings, _ = fit_style_controlled_bt(sample_battles, models)
            for model in models:
                bootstrap_ratings[model].append(sample_ratings[model])
        except Exception:
            # Skip failed bootstrap samples
            continue

    # Compute confidence intervals
    results = []
    for model in models:
        boot_values = bootstrap_ratings[model]
        if len(boot_values) > 0:
            p2_5 = float(np.percentile(boot_values, 2.5))
            p97_5 = float(np.percentile(boot_values, 97.5))
        else:
            p2_5 = ratings[model]
            p97_5 = ratings[model]

        results.append({
            "model_name": model,
            "median": ratings[model],
            "p2.5": p2_5,
            "p97.5": p97_5
        })

    # Create DataFrame and sort by rating
    df = pl.DataFrame(results).sort("median", descending=True)

    # Add ranks
    df = df.with_row_index("rank", offset=1)

    # Compute rank bounds
    df = compute_rank_bounds(df)

    return df


def main():
    votes = fetch_votes()
    reactions = fetch_reactions()
    conversations = fetch_conversations()

    # Standard rankings
    rankings, all_battles = compute_rankings(votes, reactions)
    match_counts = compute_match_counts(votes, reactions)
    preferences = compute_preferences(votes)
    win_rates = compute_win_rates(all_battles)
    mean_win_probs = compute_mean_win_prob(rankings)

    # Style-controlled rankings (using votes + reactions)
    style_rankings = compute_style_controlled_rankings(votes, reactions, conversations)

    # Join all data
    print("Joining data...")
    result = rankings.join(match_counts, on="model_name", how="left")
    result = result.join(preferences, on="model_name", how="left")
    result = result.join(win_rates, on="model_name", how="left")
    result = result.join(mean_win_probs, on="model_name", how="left")

    # Fill nulls
    result = result.fill_null(0)

    # Convert to dict and add style_controlled as nested object
    result_dicts = result.to_dicts()

    # Create lookup for style-controlled data
    style_lookup = {}
    if len(style_rankings) > 0:
        for row in style_rankings.to_dicts():
            style_lookup[row["model_name"]] = {
                "median": row["median"],
                "p2.5": row["p2.5"],
                "p97.5": row["p97.5"],
                "rank": row["rank"],
                "rank_p2.5": row["rank_p2.5"],
                "rank_p97.5": row["rank_p97.5"]
            }

    # Add style_controlled to each model
    for model_dict in result_dicts:
        model_name = model_dict["model_name"]
        if model_name in style_lookup:
            model_dict["style_controlled"] = style_lookup[model_name]
        else:
            model_dict["style_controlled"] = None

    # Format output
    output = {
        "timestamp": datetime.now().timestamp(),
        "models": result_dicts
    }

    print(f"Writing to {OUTPUT_PATH}...")
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Done. {len(result_dicts)} models ranked.")


if __name__ == "__main__":
    main()
