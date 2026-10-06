"""
Which votes the public ranking counts, against a real PostgreSQL database.
Runs when COMPARIA_TEST_DB_URI points at a throwaway database with the
migrations applied:

    createdb comparia_test
    COMPARIA_DB_URI=postgresql://localhost/comparia_test uv run alembic upgrade head
    COMPARIA_TEST_DB_URI=postgresql://localhost/comparia_test uv run pytest tests/ranking/test_fetch_votes_db.py

Each test empties the tables it seeds, on the way in and on the way out.
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_DB_URI = os.environ.get("COMPARIA_TEST_DB_URI", "")

os.environ.setdefault("COMPARIA_DB_URI", TEST_DB_URI or "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

import utils.database.models  # noqa: E402,F401
import utils.ranking.queries as queries  # noqa: E402
from utils.database.session import _async_url  # noqa: E402

pytestmark = pytest.mark.skipif(not TEST_DB_URI, reason="COMPARIA_TEST_DB_URI not set")

TRUNCATE = text(
    "TRUNCATE turn, llm_message, comparison, llm_data, llm_lab, llm_license CASCADE"
)
LLM_ID = uuid.uuid4()


def counted(comparisons: list[dict]) -> list[str]:
    """Seed one voted comparison per dict, run fetch_votes, and return the
    choice of each vote it counted. Each comparison votes its own `choice`."""

    async def main():
        engine = create_async_engine(_async_url(TEST_DB_URI))

        @contextlib.asynccontextmanager
        async def get_session():
            async with AsyncSession(engine) as session:
                yield session

        async def execute(sql, **params):
            async with engine.begin() as connection:
                await connection.execute(text(sql), params)

        original = queries.get_session
        queries.get_session = get_session
        try:
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await seed_model(execute)
            for comparison in comparisons:
                await add_vote(execute, **comparison)
            return sorted(vote["choice"] for vote in await queries.fetch_votes())
        finally:
            queries.get_session = original
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await engine.dispose()

    return asyncio.run(main())


async def seed_model(execute):
    lab_id, license_id = uuid.uuid4(), uuid.uuid4()
    await execute(
        "INSERT INTO llm_lab (id, created_at, updated_at, name, origin_country) "
        "VALUES (:id, now(), now(), 'Lab', 'FR')",
        id=lab_id,
    )
    await execute(
        "INSERT INTO llm_license (id, created_at, updated_at, kind, name, reuse, "
        "commercial_use) VALUES (:id, now(), now(), 'open', 'MIT', true, true)",
        id=license_id,
    )
    await execute(
        "INSERT INTO llm_data (id, created_at, updated_at, lab_id, license_id, "
        "human_id, status, name, rate_limited, release_date, arch, params, inputs, "
        "public_weights, public_training_data, public_training_code, eu_hostable, "
        "price_in, price_out, links) VALUES (:id, now(), now(), :lab, :license, "
        "'model', 'enabled', 'Model', false, :release, 'dense', 1, '[]', true, "
        "false, false, true, 0, 0, '[]')",
        id=LLM_ID,
        lab=lab_id,
        license=license_id,
        release=date(2025, 1, 1),
    )


async def add_vote(execute, choice, cohorts=None, contains_pii=None, archived=None):
    comparison_id = uuid.uuid4()
    await execute(
        "INSERT INTO comparison (id, created_at, updated_at, ip, "
        "participation_terms_version, cohorts, contains_pii, archived, mode, "
        "revealed, llm_id_a, llm_id_b) VALUES (:id, now(), now(), '203.0.113.7', "
        "'1', :cohorts, :pii, :archived, 'random', false, :llm, :llm)",
        id=comparison_id,
        cohorts=cohorts,
        pii=contains_pii,
        archived=archived,
        llm=LLM_ID,
    )
    await execute(
        "INSERT INTO turn (id, created_at, updated_at, comparison_id, choice, "
        "keyword_annotations_a, keyword_annotations_b) "
        "VALUES (:id, now(), now(), :comparison, :choice, '[]', '[]')",
        id=uuid.uuid4(),
        comparison=comparison_id,
        choice=choice,
    )


def test_an_ordinary_vote_counts():
    assert counted([{"choice": "a_better"}, {"choice": "b_better", "cohorts": ""}]) == [
        "a_better",
        "b_better",
    ]


def test_a_pix_vote_stays_out_of_the_ranking():
    assert counted(
        [{"choice": "a_better"}, {"choice": "b_better", "cohorts": "pix"}]
    ) == ["a_better"]


def test_a_vote_flagged_as_personal_stays_out_even_when_not_archived():
    assert counted(
        [
            {"choice": "a_better", "contains_pii": False},
            {"choice": "b_better", "contains_pii": True, "archived": None},
            {"choice": "both_good", "contains_pii": True, "archived": False},
        ]
    ) == ["a_better"]


def test_an_archived_vote_stays_out():
    assert counted(
        [{"choice": "a_better"}, {"choice": "b_better", "archived": True}]
    ) == ["a_better"]
