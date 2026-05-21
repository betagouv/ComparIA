# Why we should switch to tiers

## The problem with ranking 1 to 109

Right now the leaderboard shows ranks: 1, 2, 3, …, 109. That looks precise, but it isn't. We don't know the "true" strength of any model — we estimate it from pairwise battles, and every estimate has a margin of error.

For most pairs of nearby models, the margins overlap. When model #4 scores 1125 ±10 and model #7 scores 1122 ±10, the honest answer is "we can't tell them apart." But the page shows them as #4 and #7, and people read meaning into it.

This causes two opposite mistakes:

- People over-interpret small gaps. "Mistral Medium beats GPT-5.5 by three places!" — when in fact the next data refresh could swap them.
- Or they look at the bunched scores and decide the whole leaderboard is useless. Which is also wrong: the top really is meaningfully ahead of the bottom.

The data is fine. The presentation is misleading.

## What tiers do instead

Tiers group models we can't statistically tell apart. Instead of saying "#4 vs #7," we say "both in Tier A."

That sounds like we're being vaguer, but we're actually being more honest. And in exchange, the comparisons we *can* make get stronger:

- "Tier A is ahead of Tier B" is a real claim the data supports.
- "Model #5 is ahead of model #6" usually isn't.

Three things get better:

1. **Comparisons hold up.** If two models are in different tiers, their margins of error don't overlap. So you can actually say one is ahead.
2. **You can see the uncertainty.** A model with 200 battles has a much wider margin than one with 8000. With ranks, that's invisible. With tiers plus a bar chart of the margin, you see it directly.
3. **Refreshes stop looking like news.** Today, a re-fit can shuffle #5 to #15 just from noise, and people read it as "GPT-5 dropped." With tiers, the same noise leaves everyone in Tier A and nothing visible changes. Which is the truth.

The exact rank is still available in the data export for anyone who wants it. We're just changing the default view.

## How tier assignment works

Sort models by score, top to bottom. Walk the list once.

The first model opens Tier A. We remember its lower margin — call it the **anchor**.

For each next model, check: does its upper margin reach the anchor?

- **Yes** → it overlaps the tier leader's range. It joins the tier.
- **No** → it's clearly below. Start a new tier (B, C, D, …), with a new anchor at this model's lower margin.

The anchor stays fixed for the whole tier. It doesn't move down when more models join. This is the important part — earlier versions let the anchor drift, and 105 of 109 models ended up in Tier A through a chain of small overlaps. The fixed anchor stops that.

What this means for the reader: **every model in a tier is statistically indistinguishable from the tier leader.** That's the property the tier guarantees.

## How it looks

Two changes on the table:

1. **Tier badges.** One colored block per tier, letter centered, spanning all the rows in it. Same color = same tier.
2. **Score bars.** Each score becomes a horizontal bar showing the margin of error, with a dot on the point estimate. All bars share the same x-axis. You can see overlap at a glance, and you can see which models have noisy scores (wide bars) vs. confident ones (narrow bars).

Inside a tier, models are still sorted by score so the eye has an order to follow. But the tier letter is the claim we're making.

## Things to be honest about

- **The tier boundaries aren't perfect.** We're doing ~109 statistical comparisons at 95% confidence, so a handful of breaks will be off just from noise. Tiers are consistent and readable, not exact.
- **Two models can be 1 point apart and in different tiers.** This happens when one has a tighter margin than the other. It's statistically correct, but visually surprising. A tooltip on the tier badge explains it.
- **Tiers depend on what's on screen.** If you filter to open-source models only, tiers recompute on that subset. A model that's A2 globally might become A1 in the filtered view. The letters describe the current view, not a fixed identity.

None of these are dealbreakers. They're the cost of replacing a misleading number with a more honest label.

## Summary

The math under the leaderboard is fine. The way we display it isn't — integer ranks claim precision the data doesn't have, and that mismatch is where most of the confusion comes from.

Tiers fix that. Groups of models we can't tell apart look like groups. Real differences look like real differences. The change is reversible (the underlying ranks are still in the data), the algorithm is a dozen lines of code, and it has one clear rule: *everyone in a tier is indistinguishable from the tier leader at 95% confidence.*
