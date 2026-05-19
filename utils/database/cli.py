import logging

from cyclopts import App

from utils.logger import configure_logger

from .actions import (
    archive_corrupted,
    archive_spam,
    archive_unknown_llms,
    llm_analyze,
    rename_llm,
)
from .lint import lint, log_archived

cli_archive = App(name="archive", help="Individual archival utilities.")
cli_archive.command(archive_spam, name="spam")
cli_archive.command(archive_corrupted, name="corrupted")
cli_archive.command(archive_unknown_llms, name="unknown_llms")

cli_db = App(name="db", help="Database related utilities.")
cli_db.command(lint)
cli_db.command(log_archived)
cli_db.command(rename_llm)
cli_db.command(llm_analyze)
cli_db.command(cli_archive)


if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_db()
