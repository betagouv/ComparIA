"""
Which comparisons the analysis commands touch, against a real PostgreSQL
database. These run when COMPARIA_TEST_DB_URI points at a throwaway database
with the migrations applied, as in test_retention_db.py.
"""

import asyncio
import contextlib
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_DB_URI = os.environ.get("COMPARIA_TEST_DB_URI", "")

os.environ.setdefault("COMPARIA_DB_URI", TEST_DB_URI or "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402
from sqlmodel import col, select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from tests.database.test_partner_cohorts_db import add_model  # noqa: E402
from utils.database.models import Comparison, Turn  # noqa: E402
from utils.database.models.dataset_check import (  # noqa: E402
    DEFAULT_CRITERIA,
    DatasetCheck,
)
from utils.database.session import _async_url  # noqa: E402

# The package exports functions of the same names, which shadow the modules.
import utils.database.actions.analysis_reapply  # noqa: E402, F401  isort:skip
import utils.database.actions.llm_analyze  # noqa: E402, F401  isort:skip

reapply = sys.modules["utils.database.actions.analysis_reapply"]
llm_analyze = sys.modules["utils.database.actions.llm_analyze"]

pytestmark = pytest.mark.skipif(not TEST_DB_URI, reason="COMPARIA_TEST_DB_URI not set")

TRUNCATE = text(
    "TRUNCATE user_message, turn, comparison, llm_data, llm_lab, llm_license CASCADE"
)
# A comparison needs a real model: set by `run`.
LLM_ID = None
NOW = datetime(2026, 10, 5, 12, 0)
MODEL = "test/decider"
SCORES = json.dumps({"model": MODEL, "scores": {"pii": 0.0, "spam": 0.0}})


def run(scenario, monkeypatch):
    async def main():
        engine = create_async_engine(_async_url(TEST_DB_URI))

        @contextlib.asynccontextmanager
        async def get_session():
            async with AsyncSession(engine) as session:
                yield session

        async def execute(sql, **params):
            async with engine.begin() as connection:
                await connection.execute(text(sql), params)

        async def check():
            return DatasetCheck(criteria=[dict(c) for c in DEFAULT_CRITERIA])

        monkeypatch.setattr(reapply, "get_session", get_session)
        monkeypatch.setattr(reapply, "get_dataset_check", check)
        global LLM_ID
        try:
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            LLM_ID = await add_model(execute)
            return await scenario(execute, get_session)
        finally:
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await engine.dispose()

    return asyncio.run(main())


async def add(execute, *, scores="NULL", web_search=None, **fields) -> uuid.UUID:
    """A published comparison the chat model analysed, unless `fields` say
    otherwise. `scores` is SQL, so the JSON value null can be stored."""
    row = {
        "archived": False,
        "llm_analyzed": True,
        "contains_pii": False,
        "contains_spam": False,
        "cohorts": None,
        **fields,
    }
    comparison_id = uuid.uuid4()
    await execute(
        "INSERT INTO comparison (id, created_at, updated_at, ip, "
        "participation_terms_version, mode, revealed, llm_id_a, llm_id_b, "
        "archived, archived_reason, llm_analyzed, contains_pii, contains_spam, "
        "cohorts, categories, analysis_scores) VALUES (:id, :at, :at, "
        "'203.0.113.7', '1', 'random', false, :llm, :llm, :archived, "
        ":archived_reason, :llm_analyzed, :contains_pii, :contains_spam, "
        f":cohorts, '[\"Sports\"]', {scores})",
        id=comparison_id,
        at=NOW,
        llm=LLM_ID,
        archived_reason=row.pop("archived_reason", None),
        **row,
    )
    turn_id = uuid.uuid4()
    await execute(
        "INSERT INTO turn (id, created_at, updated_at, comparison_id, "
        "keyword_annotations_a, keyword_annotations_b) "
        "VALUES (:id, :at, :at, :comparison, '[]', '[]')",
        id=turn_id,
        at=NOW,
        comparison=comparison_id,
    )
    await execute(
        "INSERT INTO user_message (id, created_at, turn_id, role, content, "
        "web_search_results) VALUES (:id, :at, :turn, 'user', "
        "'Qui contacter ?', CAST(:web_search AS jsonb))",
        id=uuid.uuid4(),
        at=NOW,
        turn=turn_id,
        web_search=json.dumps(web_search) if web_search else None,
    )
    return comparison_id


async def fetch(get_session, comparison_id) -> Comparison:
    async with get_session() as session:
        return (
            await session.exec(
                select(Comparison)
                .options(selectinload(Comparison.turns).selectinload(Turn.user_msg))
                .where(col(Comparison.id) == comparison_id)
            )
        ).one()


def test_reapply_leaves_rows_without_scores_alone(monkeypatch):
    async def scenario(execute, get_session):
        held = {
            "archived": True,
            "archived_reason": "pii",
            "contains_pii": True,
        }
        json_null = await add(execute, scores="'null'::jsonb", **held)
        sql_null = await add(execute, **held)
        scored = await add(execute, scores=f"'{SCORES}'::jsonb", **held)

        await reapply.analysis_reapply(commit=True)

        for untouched in (json_null, sql_null):
            row = await fetch(get_session, untouched)
            assert row.archived and row.archived_reason == "pii"
            assert row.contains_pii and row.categories == ["Sports"]
        released = await fetch(get_session, scored)
        assert not released.archived and not released.contains_pii

    run(scenario, monkeypatch)


def test_the_analysis_reads_the_web_search_results_stored(monkeypatch):
    async def scenario(execute, get_session):
        comparison_id = await add(
            execute,
            web_search=[
                {
                    "type": "text",
                    "name": "Annuaire",
                    "url": "https://example.org",
                    "content": "Jean Dupont, jean.dupont@example.org",
                    "favicon": "",
                }
            ],
        )
        row = await fetch(get_session, comparison_id)
        assert "jean.dupont@example.org" in llm_analyze.conversation_text(row)

    run(scenario, monkeypatch)


def test_no_scores_are_stored_as_sql_null(monkeypatch):
    async def scenario(execute, get_session):
        async with get_session() as session:
            row = Comparison(
                ip="127.0.0.1",
                mode="random",
                llm_id_a=LLM_ID,
                llm_id_b=LLM_ID,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            stored = (
                await session.exec(
                    select(Comparison.id).where(
                        col(Comparison.analysis_scores).is_(None)
                    )
                )
            ).all()
        assert stored == [row.id]

    run(scenario, monkeypatch)
