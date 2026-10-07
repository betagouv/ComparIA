"""
Partner programme conversations (Pix pupils) stay out of the analysis and the
public ranking, against a real PostgreSQL database. These run when
COMPARIA_TEST_DB_URI points at a throwaway database with the migrations
applied, as in test_retention_db.py.
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

TEST_DB_URI = os.environ.get("COMPARIA_TEST_DB_URI", "")

os.environ.setdefault("COMPARIA_DB_URI", TEST_DB_URI or "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")

import pytest  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402
from sqlmodel import col, func, select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

import utils.ranking.queries as queries  # noqa: E402
from utils.database.actions.llm_analyze import TO_ANALYZE_CONDITION  # noqa: E402
from utils.database.models import Comparison  # noqa: E402
from utils.database.session import _async_url  # noqa: E402

pytestmark = pytest.mark.skipif(not TEST_DB_URI, reason="COMPARIA_TEST_DB_URI not set")

TRUNCATE = text(
    "TRUNCATE prompt_check_result, user_message, turn, comparison, llm_data, "
    "llm_lab, llm_license CASCADE"
)
NOW = datetime(2026, 10, 5, 12, 0)


def run(scenario):
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
            return await scenario(execute, get_session)
        finally:
            queries.get_session = original
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await engine.dispose()

    return asyncio.run(main())


async def add_model(execute):
    lab_id, license_id, llm_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
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
        id=llm_id,
        lab=lab_id,
        license=license_id,
        release=date(2025, 1, 1),
    )
    return llm_id


async def add_voted_comparison(execute, llm_id, cohorts):
    comparison_id = uuid.uuid4()
    await execute(
        "INSERT INTO comparison (id, created_at, updated_at, ip, "
        "participation_terms_version, cohorts, archived, mode, revealed, "
        "llm_id_a, llm_id_b) VALUES (:id, :at, :at, '203.0.113.7', '1', "
        ":cohorts, false, 'random', false, :llm, :llm)",
        id=comparison_id,
        at=NOW,
        cohorts=cohorts,
        llm=llm_id,
    )
    await execute(
        "INSERT INTO turn (id, created_at, updated_at, comparison_id, choice, "
        "keyword_annotations_a, keyword_annotations_b) "
        "VALUES (:id, :at, :at, :comparison, 'a_better', '[]', '[]')",
        id=uuid.uuid4(),
        at=NOW,
        comparison=comparison_id,
    )
    return comparison_id


def test_partner_cohorts_are_not_analysed_nor_ranked():
    async def scenario(execute, get_session):
        llm_id = await add_model(execute)
        for cohorts in (None, "", "pix"):
            await add_voted_comparison(execute, llm_id, cohorts)

        async with get_session() as session:
            to_analyze = (
                await session.exec(
                    select(func.count(col(Comparison.id))).where(TO_ANALYZE_CONDITION)
                )
            ).one()
        votes = await queries.fetch_votes()

        assert to_analyze == 2
        assert len(votes) == 2

    run(scenario)
