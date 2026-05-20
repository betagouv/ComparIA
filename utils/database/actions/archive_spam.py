import logging
import uuid

from sqlmodel import col

from backend.arena.spam_detection import is_spam

from ..models import Comparison
from ..utils import archive, get_db_comparisons_stream

logger = logging.getLogger("comparia.db")


def comparison_contains_spam(comparison: Comparison) -> bool:
    """
    Check if a comparison contains spam in user messages.

    Returns:
        True if any user message contains spam, False otherwise
    """
    for turn in comparison.turns:
        if is_spam(turn.user_msg.content):
            return True

    return False


async def archive_spam(*, commit: bool = False) -> None:
    """
    Archive comparisons for which we find spam in user messages.
    """
    logger.info("Searching for spam in comparisons.")

    ids: list[uuid.UUID] = []
    async for db_comp in get_db_comparisons_stream([col(Comparison.archived) == None]):
        if comparison_contains_spam(db_comp):
            ids.append(db_comp.id)

    if not ids:
        logger.info(f"No comparisons with spam found!")
        return

    logger.warning(f"Found {len(ids)} comparisons with spam.")

    await archive(ids, "spam", commit=commit)
