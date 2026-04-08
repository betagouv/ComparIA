import logging

from .actions import (
    archive_corrupted,
    archive_duplicate,
    archive_not_archived,
    archive_spam,
    archive_unknown_llms,
)
from .utils import reset_archived

logger = logging.getLogger("comparia.database")


def lint(*, fix: bool = False, hard: bool = False):
    """
    Run database linting.

    Will check for spam, corrupted data, unknown LLMs, duplicates and not archived votes or reaction that should be.
    Will only log what should be archived, use `--fix` to actually archive data.
    Will only check not already analyzed data, use `--hard` to analyze/fix all data except already archived data.
    """
    if hard:
        reset_archived()

    archive_spam(commit=fix)
    archive_corrupted(commit=fix)
    archive_unknown_llms(commit=fix and hard)
    archive_duplicate(commit=fix)
    archive_not_archived(commit=fix)
