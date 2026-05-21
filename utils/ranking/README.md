# Ranking

How the compar:IA leaderboard is computed, what its known limitations are, and what we plan to change.

## How it works today

### Inputs

Two sources of pairwise signal are pulled from the database in `queries.py`:

- **Votes**: a user saw responses from model A and model B side-by-side and picked one (or marked them equal). One row per A/B comparison.
- **Reactions**: a user thumbs-up'd or thumbs-down'd a single response in the same A/B context. Converted into a battle: a like = win for the liked model against the opponent shown; a dislike = win for the opponent.

Both are grouped by `country_portal` so each portal gets its own ranking, plus a global `"all"` ranking that pools everything.

### From signal to battles

`compute.py::_votes_to_battles` and `_reactions_to_battles` flatten everything into a list of `(model_a, model_b, winner)` tuples. Currently:

- Tied votes (`both_equal = true`) are **dropped**.
- Reactions are weighted identically to full votes (one battle each).

The two lists are concatenated and fed to the Bradley-Terry solver.

### Bradley-Terry solver

`bradley_terry.py::_fit_from_arrays` runs the standard MM (minorization-maximization) algorithm on pairwise win/loss data. It produces a strength parameter per model, which is converted to an Elo-like score centered at 1000:

```
elo = 400 * log10(strength) + 1000
```

A 100-point gap means the higher-rated model wins ~64% of the time; a 200-point gap, ~76%.

Models that never won or never lost in the data are marked NaN and excluded — the MLE for them is ±∞ and would poison the bootstrap.

### Confidence intervals

`bootstrap_confidence_intervals` resamples the full battle list with replacement `n_samples=500` times, refits BT on each resample, and takes the 2.5 / 97.5 percentiles per model. These bounds drive both the score CI (`score_p2_5`, `score_p97_5`) and the rank CI (`rank_p2_5`, `rank_p97_5`) shown in `DatasetData`.

Rank bounds use CI overlap:
- `rank_best` = 1 + number of models whose lower-CI is above this model's upper-CI
- `rank_worst` = N − number of models whose upper-CI is below this model's lower-CI

### Other per-model stats

- `mean_win_prob`: average `P(i beats j)` over all other ranked models, derived from point Elos.
- `win_rate`: raw wins / matches.
- `n_match`: total battles the model participated in.

Preference flags (useful, complete, creative, incorrect, …) are aggregated separately in `_aggregate_preferences` and not used in the score itself.

## Known problems

### 1. Ties are thrown away

`_votes_to_battles` skips every `both_equal` vote. This is the single biggest source of compression and inflated CIs:

- Ties carry the most information about *closeness* between two models. Dropping them removes the signal that says "these two are indistinguishable on this prompt."
- Typical tie rates on this kind of platform are 20–30% of votes. We're throwing out ~1 vote in 4.
- BT can handle ties natively by counting them as half a win for each side. LMArena does this.

### 2. The leaderboard looks more compressed than it is — and we don't visualize the uncertainty

Two things confuse readers of the current page:

- **Real compression**: a 49-point gap from #1 to #20 maps to ~57% win probability head-to-head. That *is* genuinely close, and it's mostly an artifact of the prompt population (casual general-public prompts don't discriminate strongly between frontier models). It's not a bug.
- **Visualized compression**: the page shows strict integer ranks (1, 2, 3, …) with no indication that #4 and #7 are statistically indistinguishable. The rank CI (`rank_p2_5` / `rank_p97_5`) is computed but not displayed.

Result: readers either over-interpret rank differences ("Mistral Medium beats GPT-5.5!") or under-interpret the whole board ("everything is tied, this is useless"). Neither is true.

### 3. Heterogeneous CI widths

Bootstrap resamples the full battle list, so a model with 200 battles ends up with a ±40 CI while a model with 8000 battles has ±8. This is statistically correct but visually it makes the low-vote models look tied with everyone, even when they're clearly stronger/weaker. Not planning to change the math here, but the visualization needs to make CI width visible so the reader can tell.

## What we're not changing (and why)

A few options were considered and rejected:

- **Down-weighting reactions vs. votes.** A reaction in an A/B context is the same kind of binary preference signal as a vote — there's no principled reason to treat one as worth less than the other. Mixing them 1:1 stays.
- **A separate "hard prompts" ranking.** Prompt difficulty is subjective and any classifier we'd use (length, turn count, keyword heuristics) bakes our editorial judgment into the score. We'd rather keep one honest ranking on the actual user prompt distribution than ship a "hard" ranking whose definition we have to defend.

## What we're changing

### Count ties as half-wins

In `_votes_to_battles`, replace the `both_equal` skip with emitting two battles: `(a, b, a)` and `(a, b, b)`. This is the standard BT-with-ties treatment and recovers ~25% of the dataset.

Expected effects:
- Confidence intervals narrow across the board.
- The top spreads out modestly (ties pull mean strengths together, but they also resolve close pairs that the BT solver was previously guessing on).
- No solver changes needed — the MM iteration is unchanged.

We'll re-run the full ranking once and compare before/after to confirm the direction matches expectations.

### Visualize uncertainty on the ranking page

Two coordinated changes:

1. **Tier letters instead of strict ranks.** Greedy-group from the top: model #1 plus every model whose CI overlaps its CI become Tier A; the first model whose CI doesn't overlap A starts Tier B; etc. Display as "A1, A2, …, B1, B2, …" The data for this is already in `rank_p2_5` / `rank_p97_5`.
2. **Forest-plot row.** Replace (or augment) the numeric score column with a horizontal bar from `score_p2_5` to `score_p97_5`, with a dot on the point estimate, all on a shared x-axis. Readers see overlap at a glance and the heterogeneous CI widths from problem #3 become legible instead of misleading.

## Tier system design

### Tier computation

Greedy pass top-down on the score-sorted list:

```
tier = "A"
current_tier_lower_ci = scores[0].lower

for model in scores:
    if model.upper < current_tier_lower_ci:
        # CI no longer overlaps the running tier band → start new tier
        tier = next_letter(tier)
        current_tier_lower_ci = model.lower
    else:
        # extend the band downward to this model's lower CI
        current_tier_lower_ci = min(current_tier_lower_ci, model.lower)
    model.tier = tier
```

The band-extension rule (running minimum of lower CIs) prevents a long chain of "each model overlaps the previous one" from collapsing everything into Tier A. A model only joins the current tier if its upper CI still overlaps the *narrowed* band, not just the immediate predecessor.

Within tier, order by point Elo descending and label `A1, A2, …`.

### Visual anatomy

```
Tier  Model                       Votes   Score (95% CI)
 A1   gemini-3-flash-preview      4,210   ├──●──┤  1142
 A2   gemini-3.1-pro-preview      3,880    ├──●──┤ 1139
 A3   mistral-medium-2508         5,120    ├─●─┤   1130
 ──────────────────────────── Tier B ─────────────────
 B1   gemini-2.5-flash            7,640      ├●┤    1116
```

Columns:

- **Tier**: badge with letter + within-tier index. Same letter = same background tint so the eye groups them without needing the divider.
- **Model**: name, no rank number.
- **Votes**: `n_match`. Helps the reader interpret CI width (wide bar = few votes).
- **Score (95% CI)**: shared x-axis across the whole table. Bar from `score_p2_5` to `score_p97_5`, dot on the point estimate, numeric label on the right. Bar width visually encodes uncertainty (the heterogeneous-CI problem from #3).

Divider row between tiers is the structural marker; the badge tint is the at-a-glance one.

### Edge cases

- **Single-model tier**: model gets `A1` (no `A2`). Divider still renders below it.
- **Tier with one outlier wide CI**: the band-extension rule already handles this — the wide CI extends the band and may absorb the next model. That's intentional: if the band overlaps, they belong together.
- **More than 26 tiers**: not expected in practice (~110 models, expect 6–10 tiers). If it happens, roll to `AA, AB, …`.
- **Filtered views** (by energy, license, etc.): recompute tiers on the filtered subset. A model that's `A2` globally might be `A1` in the "open source only" view. Tier letters are relative to what's on screen.

### Shared x-axis

The score axis should span roughly `[min(lower_CI) − 10, max(upper_CI) + 10]` across the *unfiltered* board, then stay fixed when filtering — otherwise bars rescale every time the user changes a filter and visual comparisons break across views.

### Hover / detail

On bar hover: tooltip with `point Elo`, `[lower, upper]`, `n_match`, `mean_win_prob`, `win_rate`. All already in `DatasetData`.

### Where tier assignment lives

Tier letters could be computed frontend-side from `score_p2_5` / `score_p97_5` (already in `DatasetData`), but it's cleaner to compute them server-side in `_compute_rankings_for_group` and add a `tier: str` field to `DatasetData`. That way the same tier assignment is consistent across the API, exports, and any downstream consumers.

## File map

- `bradley_terry.py` — MM solver and bootstrap CIs. Pure numpy, no DB.
- `queries.py` — SQL for votes and reactions.
- `compute.py` — orchestration: fetch → battles → BT → per-portal results.
- `run.py` — scheduler entry point.
- `monitor.py` — observability for the scheduled job.
