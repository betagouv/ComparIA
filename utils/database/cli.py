import logging

from cyclopts import App

from utils.logger import configure_logger

from .actions import (
    archive_blacklisted_grok,
    archive_corrupted,
    archive_spam,
    backfill_pii_spam,
    llm_analyze,
    migrate_comparisons,
    migrate_llm_messages,
    migrate_reactions,
    migrate_reasoning_content,
    migrate_system_messages,
    migrate_turns,
    migrate_user_messages,
    migrate_votes,
)
from .lint import lint, log_archived

cli_archive = App(name="archive", help="Individual archival utilities.")
cli_archive.command(archive_spam, name="spam")
cli_archive.command(archive_corrupted, name="corrupted")
cli_archive.command(archive_blacklisted_grok, name="blacklisted_grok")

cli_migrate = App(
    name="migrate", help="Migrate data from old schema to new SQLModel schema."
)
cli_migrate.command(migrate_system_messages, name="system_messages")
cli_migrate.command(migrate_comparisons, name="comparisons")
cli_migrate.command(migrate_llm_messages, name="llm_messages")
cli_migrate.command(migrate_user_messages, name="user_messages")
cli_migrate.command(migrate_turns, name="turns")
cli_migrate.command(migrate_votes, name="votes")
cli_migrate.command(migrate_reactions, name="reactions")
cli_migrate.command(migrate_reasoning_content, name="reasoning_content")

cli_db = App(name="db", help="Database related utilities.")
cli_db.command(lint)
cli_db.command(log_archived)
cli_db.command(llm_analyze)
cli_db.command(backfill_pii_spam)
cli_db.command(cli_archive)
cli_db.command(cli_migrate)


if __name__ == "__main__":
    configure_logger(logging.getLogger("comparia"))
    cli_db()
