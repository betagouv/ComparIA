import logging

from sqlmodel import col, func, select

from utils.database.actions.llm_analyze import (
    analyze_comparisons,
    get_analysis,
    rescore_condition,
)
from utils.database.models import Comparison
from utils.database.session import get_session

logger = logging.getLogger("comparia.db")


async def analysis_rescore(*, commit: bool = False, every: bool = False) -> None:
    """
    Score the published comparisons again with the dataset check as it is now:
    the ones the chat model analysed or another decision model scored, or all
    of them with 'every' (after adding a criterion, say). They get new topics,
    languages and scores, and are held back if a criterion is reached. Held
    rows are left alone and a row that cannot be scored keeps what it had, so
    nothing is published that was not. Only counts by default, set 'commit'
    to call the model. Rows done are skipped when run again.
    """
    analysis = await get_analysis()
    async with get_session() as session:
        count = (
            await session.exec(
                select(func.count(col(Comparison.id))).where(
                    rescore_condition(analysis.model, every)
                )
            )
        ).one()
    if not commit:
        logger.warning(
            f"Would score {count} published comparisons again with "
            f"'{analysis.model}' (dry-run)."
        )
        return
    if not count:
        logger.warning("No published comparison to score again.")
        return

    analyzer = await analyze_comparisons(rescore=True, every=every)
    logger.warning(
        f"Scored {analyzer.analyzed} of {count} comparisons again: "
        f"{analyzer.held} now held back, {len(analyzer.failed)} kept as they "
        "were because they could not be scored."
    )
