import logging
from collections import Counter

from sqlmodel import col, select

from utils.database.actions.llm_analyze import SCORED, update_from_scores
from utils.database.dataset_checks import get_dataset_check
from utils.database.models import Comparison
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")

BATCH = 1_000


async def analysis_reapply(*, commit: bool = False) -> None:
    """
    Recompute the flags, topics, languages and archived fields of the
    comparisons the decision model scored, with the thresholds in force now,
    without calling the model. Only counts what would change by default, set
    'commit' to write it.

    A criterion added after a row was scored has no score on it and never
    reaches its threshold there: only the model can apply a new rule.
    """
    check = await get_dataset_check()
    criteria = check.typed_criteria
    changes: Counter[str] = Counter()
    unscored: Counter[str] = Counter()
    last_id = None
    while True:
        async with get_session() as session:
            query = (
                select(Comparison)
                .where(SCORED)
                .order_by(col(Comparison.id))
                .limit(BATCH)
            )
            if last_id is not None:
                query = query.where(col(Comparison.id) > last_id)
            rows = (await session.exec(query)).all()
            if not rows:
                break
            last_id = rows[-1].id

            for row in rows:
                stored = row.analysis_scores
                scores = stored.get("scores", {})
                for c in criteria:
                    if c.key not in scores:
                        unscored[c.key] += 1
                new = update_from_scores(
                    scores,
                    stored.get("model", ""),
                    criteria,
                    check.category_threshold,
                    check.language_threshold,
                )
                changed = _apply(row, new, changes)
                if changed and commit:
                    session.add(row)
            if commit:
                await session.commit()
            else:
                await session.rollback()

    lines = [
        f"{'Changed' if commit else 'Would change (dry-run)'}:",
        f"- {changes['excluded']} comparisons newly kept out of the dataset",
        f"- {changes['released']} comparisons released for publication",
        f"- {changes['categories']} with other topics",
        f"- {changes['languages']} with other languages",
    ]
    for key, count in unscored.items():
        lines.append(
            f"Criterion '{key}' has no score on {count} comparisons: only the "
            "model can apply it there."
        )
    logger.warning("\n".join(lines))


def _apply(row: Comparison, new, changes: Counter) -> bool:
    """Copy what moved onto `row`, counting it. Rows archived for another
    reason (corrupted, say) keep their archived fields."""
    changed = False
    if row.categories != new.categories:
        changes["categories"] += 1
        row.categories = new.categories
        changed = True
    if sorted(row.languages or []) != sorted(new.languages):
        changes["languages"] += 1
        row.languages = new.languages
        changed = True
    if (row.contains_pii, row.contains_spam) != (new.contains_pii, new.contains_spam):
        row.contains_pii = new.contains_pii
        row.contains_spam = new.contains_spam
        changed = True
    was_archived = bool(row.archived)
    if row.archived_reason in (None, "pii", "spam") and (
        was_archived != new.archived or row.archived_reason != new.archived_reason
    ):
        if new.archived and not was_archived:
            changes["excluded"] += 1
            row.archived_at = new.archived_at
        elif was_archived and not new.archived:
            changes["released"] += 1
            row.archived_at = None
        row.archived = new.archived
        row.archived_reason = new.archived_reason
        changed = True
    return changed
