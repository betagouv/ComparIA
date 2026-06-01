from cyclopts import App

from . import (
    migrate_comparisons,
    migrate_llm_messages,
    migrate_reactions,
    migrate_reasoning_content,
    migrate_system_messages,
    migrate_turns,
    migrate_user_messages,
    migrate_votes,
)

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
