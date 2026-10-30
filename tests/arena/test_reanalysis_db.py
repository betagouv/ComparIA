"""
A turn added after the analysis sends the comparison back to it, so the open
dataset never publishes text the analysis did not read. Against a real
PostgreSQL database; runs when COMPARIA_TEST_DB_URI points at a throwaway
database with the migrations applied, as in test_retention_db.py.
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
from sqlmodel import col, select  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

import backend.arena.services as services  # noqa: E402
from utils.database.actions.llm_analyze import TO_ANALYZE_CONDITION  # noqa: E402
from utils.database.models import Comparison  # noqa: E402
from utils.database.session import _async_url  # noqa: E402

pytestmark = pytest.mark.skipif(not TEST_DB_URI, reason="COMPARIA_TEST_DB_URI not set")

TRUNCATE = text(
    "TRUNCATE prompt_check_result, user_message, turn, comparison, llm_data, "
    "llm_lab, llm_license CASCADE"
)


def test_a_new_turn_sends_an_analysed_comparison_back_to_analysis():
    async def main():
        engine = create_async_engine(_async_url(TEST_DB_URI))
        sessions: list[AsyncSession] = []

        # add_comparison_turn reads the comparison back after its session
        # block, which opens a transaction nobody closes; close them all
        # before cleaning up, or the TRUNCATE waits on it forever.
        @contextlib.asynccontextmanager
        async def get_session():
            async with AsyncSession(engine) as session:
                sessions.append(session)
                yield session

        async def execute(sql, **params):
            async with engine.begin() as connection:
                await connection.execute(text(sql), params)

        async def to_analyze():
            async with get_session() as session:
                return (
                    await session.exec(
                        select(col(Comparison.id)).where(TO_ANALYZE_CONDITION)
                    )
                ).all()

        original = services.get_session
        services.get_session = get_session
        try:
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            comparison_id = await add_analysed_comparison(execute)
            assert await to_analyze() == []

            await services.add_comparison_turn(comparison_id, "Et en hiver ?")

            assert await to_analyze() == [comparison_id]
        finally:
            services.get_session = original
            for session in sessions:
                await session.close()
            async with engine.begin() as connection:
                await connection.execute(TRUNCATE)
            await engine.dispose()

    asyncio.run(main())


async def add_analysed_comparison(execute):
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
    comparison_id = uuid.uuid4()
    await execute(
        "INSERT INTO comparison (id, created_at, updated_at, ip, "
        "participation_terms_version, archived, llm_analyzed, contains_pii, "
        "contains_spam, mode, revealed, llm_id_a, llm_id_b) VALUES (:id, now(), "
        "now(), '203.0.113.7', '1', false, true, false, false, 'random', false, "
        ":llm, :llm)",
        id=comparison_id,
        llm=llm_id,
    )
    return comparison_id
