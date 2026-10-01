"""
The cli command that blanks the Matomo visitor id older comparisons still
hold, against a throwaway Postgres.

Run with pytest:
    uv run --group dev pytest tests/database/test_clear_visitor_ids.py
"""

import importlib
import logging
import uuid

from sqlalchemy import text
from sqlmodel import col, select

from utils.database.models.comparison import Comparison
from utils.database.session import get_session

# The package re-exports the function under the module's name.
action = importlib.import_module("utils.database.actions.clear_visitor_ids")


async def add_comparisons(*visitor_ids):
    async with get_session() as session:
        # The ids point at no LLM: skip the foreign keys rather than build a
        # catalogue the command never reads.
        await session.execute(text("SET session_replication_role = replica"))
        for visitor_id in visitor_ids:
            session.add(
                Comparison(
                    ip="192.0.2.10",
                    visitor_id=visitor_id,
                    mode="random",
                    llm_id_a=uuid.uuid4(),
                    llm_id_b=uuid.uuid4(),
                )
            )
        await session.commit()


async def stored_visitor_ids():
    async with get_session() as session:
        rows = await session.exec(
            select(Comparison.visitor_id).order_by(col(Comparison.visitor_id))
        )
        return list(rows.all())


def test_the_dry_run_counts_and_changes_nothing(database, caplog):
    async def scenario():
        await add_comparisons("aaa", "bbb", None)
        with caplog.at_level(logging.WARNING, logger="comparia.db"):
            await action.clear_visitor_ids()
        assert "2 comparisons hold a visitor id" in caplog.text
        assert await stored_visitor_ids() == ["aaa", "bbb", None]

    database(scenario)


def test_commit_clears_every_visitor_id_in_batches(database):
    async def scenario():
        await add_comparisons("aaa", "bbb", "ccc", None)
        await action.clear_visitor_ids(commit=True, batch_size=2)
        assert await stored_visitor_ids() == [None, None, None, None]

    database(scenario)


def test_the_command_is_wired_into_comparia_cli():
    from utils.database.cli import cli_db

    assert "clear-visitor-ids" in cli_db
