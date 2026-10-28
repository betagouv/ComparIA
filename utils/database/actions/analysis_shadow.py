import logging
from collections import Counter

from sqlalchemy.orm import selectinload
from sqlmodel import col, func, or_, select

from utils.database.actions.llm_analyze import (
    NO_COHORT,
    SCORED,
    AnalysisStopped,
    conversation_text,
    get_analysis,
    score_comparison,
    stopping_status,
    update_from_scores,
)
from utils.database.models import Comparison, Turn
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")

# How many rows that differ the report lists, so a big sample stays readable.
SHOWN = 30


async def analysis_shadow(*, sample: int = 500) -> None:
    """
    Score a random sample of comparisons the chat model already analysed with
    the dataset check's decision model, and compare. Writes nothing: run it
    before switching an instance over, then tune the thresholds and wording.
    """
    analysis = await get_analysis()
    async with get_session() as session:
        rows = (
            await session.exec(
                select(Comparison)
                .options(
                    selectinload(Comparison.turns).options(
                        selectinload(Turn.user_msg),
                        selectinload(Turn.llm_msg_a),
                        selectinload(Turn.llm_msg_b),
                    )
                )
                .where(
                    col(Comparison.llm_analyzed) == True,  # noqa: E712
                    ~SCORED,
                    NO_COHORT,
                    # Archived for being corrupted, not for what it says.
                    or_(
                        col(Comparison.archived_reason).is_(None),
                        col(Comparison.archived_reason).in_(["pii", "spam"]),
                    ),
                )
                .order_by(func.random())
                .limit(sample)
            )
        ).all()

    if not rows:
        logger.warning("No comparison analysed by the chat model to compare with.")
        return

    flags: Counter[tuple[str, bool, bool]] = Counter()
    differing = []
    overlap = []
    languages_agree = 0
    failed = 0
    for row in rows:
        try:
            scores = await score_comparison(conversation_text(row), analysis)
        except Exception as e:
            if status := stopping_status(e):
                raise AnalysisStopped(f"OpenRouter answered {status}") from e
            failed += 1
            logger.warning(f"Could not score '{row.id}': {e!r}")
            continue
        new = update_from_scores(
            scores,
            analysis.model,
            analysis.criteria,
            analysis.category_threshold,
            analysis.language_threshold,
        )
        for flag in ("contains_pii", "contains_spam"):
            old_value, new_value = bool(getattr(row, flag)), getattr(new, flag)
            flags[(flag, old_value, new_value)] += 1
            if old_value != new_value:
                differing.append((row.id, flag, old_value, scores))
        old_categories, new_categories = set(row.categories or []), set(new.categories)
        if old_categories or new_categories:
            overlap.append(
                len(old_categories & new_categories)
                / len(old_categories | new_categories)
            )
        languages_agree += set(row.languages or []) == set(new.languages)

    scored = len(rows) - failed
    lines = [f"Scored {scored} of {len(rows)} comparisons ({failed} failed)."]
    for flag in ("contains_pii", "contains_spam"):
        same = flags[(flag, False, False)] + flags[(flag, True, True)]
        lines.append(
            f"{flag}: {same}/{scored} agree, "
            f"{flags[(flag, False, True)]} newly flagged, "
            f"{flags[(flag, True, False)]} no longer flagged"
        )
    if overlap:
        lines.append(f"Topics: {sum(overlap) / len(overlap):.0%} overlap on average")
    lines.append(f"Languages: {languages_agree}/{scored} identical")
    if differing:
        lines.append(f"Rows that differ (first {min(SHOWN, len(differing))}):")
        for comparison_id, flag, old_value, scores in differing[:SHOWN]:
            excluding = {
                c.key: round(scores.get(c.key, 0.0), 3) for c in analysis.criteria
            }
            lines.append(
                f"- {comparison_id} {flag}: was {old_value}, scores {excluding}"
            )
    logger.warning("\n".join(lines))
