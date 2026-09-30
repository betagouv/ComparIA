"""Tests that run the suggestion queries against a real PostgreSQL database.

The rest of the suite stubs the service layer, so the SQL itself is never
executed. These tests fill that gap. They need a throwaway database, pointed at
by COMPARIA_TEST_DB_URI, and they skip when it is not set:

    createdb comparia_test_suggestions
    COMPARIA_DB_URI=postgresql://localhost/comparia_test_suggestions \\
        uv run alembic upgrade head
    COMPARIA_TEST_DB_URI=postgresql://localhost/comparia_test_suggestions \\
        uv run --with pytest --with httpx --with greenlet pytest tests/ -q

The models use JSONB and the PostgreSQL TIMESTAMP type, so SQLite is not an
option. Every test empties the suggestion tables first, which is why the
database must be a throwaway one and never a development database.
"""

import asyncio
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable

import pytest

TEST_DB_URI = os.environ.get("COMPARIA_TEST_DB_URI", "")

os.environ.setdefault("COMPARIA_DB_URI", TEST_DB_URI or "postgresql://x/y")
os.environ.setdefault("LOG_FORMAT", "JSON")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

import backend.suggestions.services as suggestion_services
from backend.suggestions.services import (
    list_admin_suggestions,
    list_public_suggestions,
    set_suggestion_category_archived,
)
from utils.database.models.auth import User
from utils.database.models.suggestion import (
    PromptSuggestion,
    SuggestionCategory,
    SuggestionCreate,
)

requires_test_db = pytest.mark.skipif(
    not TEST_DB_URI,
    reason="set COMPARIA_TEST_DB_URI to a throwaway PostgreSQL database",
)

BASE_TIME = datetime(2026, 1, 1, 12, 0, 0)
TRUNCATE = "TRUNCATE prompt_suggestion, suggestion_category, auth_user CASCADE"


def _clear_public_suggestions_cache() -> None:
    suggestion_services.invalidate_cache(suggestion_services.REDIS_SUGGESTIONS_KEY)


def _async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _run(scenario: Callable[[AsyncSession], Awaitable[Any]]) -> Any:
    """Run `scenario` with the service layer bound to the test database.

    A fresh engine per test keeps every connection inside the event loop that
    asyncio.run creates, and the tables are emptied on the way in and on the way
    out so the tests can run in any order.
    """

    async def main() -> Any:
        engine = create_async_engine(_async_url(TEST_DB_URI))

        @asynccontextmanager
        async def session_scope() -> AsyncIterator[AsyncSession]:
            async with AsyncSession(engine) as session:
                yield session

        original_get_session = suggestion_services.get_session
        suggestion_services.get_session = session_scope  # type: ignore[assignment]
        try:
            async with engine.begin() as connection:
                await connection.execute(text(TRUNCATE))
            _clear_public_suggestions_cache()
            async with session_scope() as session:
                return await scenario(session)
        finally:
            suggestion_services.get_session = original_get_session  # type: ignore[assignment]
            async with engine.begin() as connection:
                await connection.execute(text(TRUNCATE))
            _clear_public_suggestions_cache()
            await engine.dispose()

    return asyncio.run(main())


def _category(
    category_id: uuid.UUID, key: str, title: str, locale: str, display_order: int
) -> SuggestionCategory:
    return SuggestionCategory(
        id=category_id,
        locale=locale,  # type: ignore[arg-type]
        key=key,
        title=title,
        description=f"Description {title}",
        icon="i-ri-draft-line",
        display_order=display_order,
    )


def _suggestion(
    category_id: uuid.UUID,
    text_value: str,
    minutes: int,
    *,
    archived: bool = False,
) -> PromptSuggestion:
    moment = BASE_TIME + timedelta(minutes=minutes)
    return PromptSuggestion(
        category_id=category_id,
        text=text_value,
        created_at=moment,
        updated_at=moment,
        archived_at=BASE_TIME + timedelta(minutes=minutes + 30) if archived else None,
    )


async def _seed(session: AsyncSession) -> dict[str, uuid.UUID]:
    """Two French categories out of display order, plus one Danish one.

    The ids are generated here rather than read back from the objects: the
    session expires everything on commit, exactly as it does in production.
    """
    ids = {
        "alpha": uuid.uuid4(),
        "beta": uuid.uuid4(),
        "dansk": uuid.uuid4(),
    }
    session.add_all(
        [
            _category(ids["alpha"], "alpha", "Alpha", "fr", display_order=1),
            _category(ids["beta"], "beta", "Beta", "fr", display_order=0),
            _category(ids["dansk"], "dansk", "Dansk", "da", display_order=0),
        ]
    )
    await session.commit()

    session.add_all(
        [
            _suggestion(ids["alpha"], "alpha available one", 1),
            _suggestion(ids["alpha"], "alpha available two", 2),
            _suggestion(ids["alpha"], "alpha archived lettre", 3, archived=True),
            _suggestion(ids["beta"], "beta available lettre", 5),
            _suggestion(ids["dansk"], "dansk available", 6),
        ]
    )
    await session.commit()
    return ids


@requires_test_db
def test_public_suggestions_group_by_category_in_display_order() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        response = await list_public_suggestions("fr")

        assert [category.key for category in response.categories] == ["beta", "alpha"]
        assert [
            suggestion.text for suggestion in response.categories[0].suggestions
        ] == ["beta available lettre"]
        assert [
            suggestion.text for suggestion in response.categories[1].suggestions
        ] == ["alpha available one", "alpha available two"]

    _run(scenario)


@requires_test_db
def test_public_suggestions_exclude_archived_ones() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        response = await list_public_suggestions("fr")

        texts = [
            suggestion.text
            for category in response.categories
            for suggestion in category.suggestions
        ]
        assert "alpha archived lettre" not in texts
        assert len(texts) == 3

    _run(scenario)


@requires_test_db
def test_restoring_category_preserves_individually_archived_suggestions() -> None:
    async def scenario(session: AsyncSession) -> None:
        seeded = await _seed(session)
        admin_id = uuid.uuid4()
        session.add(User(id=admin_id, email="admin@example.org", role="admin"))
        await session.commit()

        archived_category = await set_suggestion_category_archived(
            seeded["alpha"], archived=True, updated_by=admin_id
        )
        assert archived_category.archived is True
        assert archived_category.available_suggestion_count == 2

        hidden = await list_public_suggestions("fr")
        assert {category.key for category in hidden.categories} == {"beta"}

        restored_category = await set_suggestion_category_archived(
            seeded["alpha"], archived=False, updated_by=admin_id
        )
        assert restored_category.archived is False
        assert restored_category.available_suggestion_count == 2

        restored = await list_public_suggestions("fr")
        alpha = next(
            category for category in restored.categories if category.key == "alpha"
        )
        assert [suggestion.text for suggestion in alpha.suggestions] == [
            "alpha available one",
            "alpha available two",
        ]

    _run(scenario)


@requires_test_db
def test_public_suggestions_are_empty_for_a_locale_without_rows() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        response = await list_public_suggestions("sv")

        assert response.categories == []

    _run(scenario)


@requires_test_db
def test_public_suggestions_are_served_from_the_cache_until_invalidated() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)
        assert len((await list_public_suggestions("fr")).categories) == 2

        for row in (await session.exec(select(PromptSuggestion))).all():
            await session.delete(row)
        await session.commit()

        assert len((await list_public_suggestions("fr")).categories) == 2
        _clear_public_suggestions_cache()
        assert (await list_public_suggestions("fr")).categories == []

    _run(scenario)


@requires_test_db
def test_creating_a_suggestion_invalidates_the_public_cache() -> None:
    async def scenario(session: AsyncSession) -> None:
        seeded = await _seed(session)
        admin_id = uuid.uuid4()
        session.add(User(id=admin_id, email="admin@example.org", role="admin"))
        await session.commit()
        await list_public_suggestions("fr")

        await suggestion_services.create_suggestion(
            SuggestionCreate(category_id=seeded["beta"], text="beta brand new"),
            created_by=admin_id,
        )

        response = await list_public_suggestions("fr")
        texts = [
            suggestion.text
            for category in response.categories
            for suggestion in category.suggestions
        ]
        assert "beta brand new" in texts

    _run(scenario)


@requires_test_db
def test_admin_suggestions_return_every_row_and_category_counts() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        suggestions, total, categories = await list_admin_suggestions()

        assert total == 5
        # French categories first, then suggestions available within each category.
        assert [suggestion.text for suggestion in suggestions] == [
            "beta available lettre",
            "alpha available two",
            "alpha available one",
            "alpha archived lettre",
            "dansk available",
        ]
        assert [
            (category.key, category.suggestion_count) for category in categories
        ] == [
            ("beta", 1),
            ("alpha", 3),
            ("dansk", 1),
        ]

    _run(scenario)


@requires_test_db
def test_admin_suggestions_sort_archived_categories_last() -> None:
    async def scenario(session: AsyncSession) -> None:
        seeded = await _seed(session)
        admin_id = uuid.uuid4()
        session.add(User(id=admin_id, email="admin@example.org", role="admin"))
        await session.commit()

        await set_suggestion_category_archived(
            seeded["beta"], archived=True, updated_by=admin_id
        )
        suggestions, _, categories = await list_admin_suggestions()

        assert suggestions[-1].text == "beta available lettre"
        assert categories[-1].key == "beta"
        assert categories[-1].archived is True

    _run(scenario)


@requires_test_db
def test_admin_suggestions_search_matches_the_text_case_insensitively() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        suggestions, total, _ = await list_admin_suggestions(search="LETTRE")

        assert total == 2
        assert {suggestion.text for suggestion in suggestions} == {
            "alpha archived lettre",
            "beta available lettre",
        }

    _run(scenario)


@requires_test_db
def test_admin_suggestions_filter_on_status() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        available, available_total, _ = await list_admin_suggestions(status="available")
        archived, archived_total, _ = await list_admin_suggestions(status="archived")

        assert available_total == 4
        assert all(suggestion.status == "available" for suggestion in available)
        assert archived_total == 1
        assert [suggestion.text for suggestion in archived] == ["alpha archived lettre"]

    _run(scenario)


@requires_test_db
def test_admin_suggestions_filter_on_locale() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        french, french_total, _ = await list_admin_suggestions(locale="fr")
        danish, danish_total, _ = await list_admin_suggestions(locale="da")

        assert french_total == 4
        assert all(suggestion.locale == "fr" for suggestion in french)
        assert danish_total == 1
        assert [suggestion.text for suggestion in danish] == ["dansk available"]

    _run(scenario)


@requires_test_db
def test_admin_suggestions_filter_on_category() -> None:
    async def scenario(session: AsyncSession) -> None:
        seeded = await _seed(session)

        suggestions, total, _ = await list_admin_suggestions(
            category_id=seeded["alpha"]
        )

        assert total == 3
        assert {suggestion.category_title for suggestion in suggestions} == {"Alpha"}

    _run(scenario)


@requires_test_db
def test_admin_suggestions_combine_filters() -> None:
    async def scenario(session: AsyncSession) -> None:
        seeded = await _seed(session)

        suggestions, total, _ = await list_admin_suggestions(
            search="lettre",
            status="available",
            locale="fr",
            category_id=seeded["beta"],
        )

        assert total == 1
        assert [suggestion.text for suggestion in suggestions] == [
            "beta available lettre"
        ]

    _run(scenario)


@requires_test_db
def test_admin_suggestions_paginate_without_losing_the_total() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        pages = []
        for page in (1, 2, 3):
            suggestions, total, _ = await list_admin_suggestions(page=page, page_size=2)
            assert total == 5
            pages.append([suggestion.text for suggestion in suggestions])

        assert pages == [
            ["beta available lettre", "alpha available two"],
            ["alpha available one", "alpha archived lettre"],
            ["dansk available"],
        ]

    _run(scenario)


@requires_test_db
def test_admin_suggestions_return_nothing_for_an_unknown_category() -> None:
    async def scenario(session: AsyncSession) -> None:
        await _seed(session)

        suggestions, total, categories = await list_admin_suggestions(
            category_id=uuid.uuid4()
        )

        assert suggestions == []
        assert total == 0
        assert len(categories) == 3

    _run(scenario)
