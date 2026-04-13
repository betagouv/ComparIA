import logging

from cyclopts import App

from utils.logger import configure_logger

from .actions import (
    archive_corrupted,
    archive_duplicate,
    archive_not_archived,
    archive_spam,
    archive_unknown_llms,
    rename_llm,
)
from .lint import lint

configure_logger(logging.getLogger("comparia.database"))

cli_archive = App(name="archive", help="Individual archival utilities.")
# cli_archive.command(archive_spam, name="spam") FIXME rm? done in topic_pii.py
cli_archive.command(archive_corrupted, name="corrupted")
cli_archive.command(archive_unknown_llms, name="unknown_llms")
cli_archive.command(archive_duplicate, name="duplicate")
cli_archive.command(archive_not_archived, name="not_archive")

cli_db = App(name="db", help="Database related utilities.")
cli_db.command(lint)
cli_db.command(rename_llm)
cli_db.command(cli_archive)


if __name__ == "__main__":
    cli_db()
