import re
import unicodedata
import uuid
from datetime import datetime

from sqlalchemy import nulls_first
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, func, select

from utils.database.models.suggestion import (
    AdminSuggestion,
    AdminSuggestionCategory,
    PromptSuggestion,
    PublicSuggestion,
    PublicSuggestionCategory,
    PublicSuggestionsResponse,
    SuggestionCategory,
    SuggestionCategoryCreate,
    SuggestionCreate,
    SuggestionLocale,
)
from utils.database.models.utils import escape_like
from utils.database.session import get_session
from utils.storage.redis import REDIS_SUGGESTIONS_KEY, invalidate_cache, redis_cache


class SuggestionCategoryNotFoundError(Exception):
    pass


class SuggestionNotFoundError(Exception):
    pass


class SuggestionAlreadyExistsError(Exception):
    pass


class SuggestionCategoryAlreadyExistsError(Exception):
    pass


class SuggestionCategoryNotEmptyError(Exception):
    pass


class SuggestionCategoryTitleUnusableError(Exception):
    pass


def _to_admin_category(
    category: SuggestionCategory,
    *,
    suggestion_count: int = 0,
    available_suggestion_count: int = 0,
) -> AdminSuggestionCategory:
    return AdminSuggestionCategory(
        id=category.id,
        locale=category.locale,
        key=category.key,
        title=category.title,
        description=category.description,
        icon=category.icon,
        tooltip=category.tooltip,
        display_order=category.display_order,
        archived=category.archived_at is not None,
        suggestion_count=suggestion_count,
        available_suggestion_count=available_suggestion_count,
    )


def _to_admin_suggestion(
    suggestion: PromptSuggestion, category: SuggestionCategory
) -> AdminSuggestion:
    return AdminSuggestion(
        id=suggestion.id,
        text=suggestion.text,
        locale=category.locale,
        category_id=category.id,
        category_title=category.title,
        status="archived" if suggestion.archived_at else "available",
        created_at=suggestion.created_at,
        updated_at=suggestion.updated_at,
    )


@redis_cache(REDIS_SUGGESTIONS_KEY)
async def list_public_suggestions(
    locale: SuggestionLocale,
) -> PublicSuggestionsResponse:
    async with get_session() as session:
        result = await session.exec(
            select(SuggestionCategory, PromptSuggestion)
            .join(PromptSuggestion)
            .where(
                col(SuggestionCategory.locale) == locale,
                col(SuggestionCategory.archived_at).is_(None),
                col(PromptSuggestion.archived_at).is_(None),
            )
            .order_by(
                col(SuggestionCategory.display_order),
                col(PromptSuggestion.created_at),
            )
        )
        categories: dict[uuid.UUID, PublicSuggestionCategory] = {}
        for category, suggestion in result.all():
            current = categories.get(category.id)
            if current is None:
                current = PublicSuggestionCategory(
                    id=category.id,
                    key=category.key,
                    title=category.title,
                    description=category.description,
                    icon=category.icon,
                    tooltip=category.tooltip,
                    suggestions=[],
                )
                categories[category.id] = current
            current.suggestions.append(
                PublicSuggestion(id=suggestion.id, text=suggestion.text)
            )
        return PublicSuggestionsResponse(categories=list(categories.values()))


async def list_admin_suggestions(
    *,
    search: str | None = None,
    status: str | None = None,
    locale: SuggestionLocale | None = None,
    category_id: uuid.UUID | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AdminSuggestion], int, list[AdminSuggestionCategory]]:
    async with get_session() as session:
        available_suggestion = aliased(PromptSuggestion)
        category_has_available_suggestions = (
            select(available_suggestion.id)
            .where(
                available_suggestion.category_id == SuggestionCategory.id,
                available_suggestion.archived_at.is_(None),
            )
            .correlate(SuggestionCategory)
            .exists()
        )
        filters: list[ColumnElement[bool]] = []
        if search:
            filters.append(
                col(PromptSuggestion.text).ilike(
                    f"%{escape_like(search.strip())}%", escape="\\"
                )
            )
        if status == "available":
            filters.append(col(PromptSuggestion.archived_at).is_(None))
        elif status == "archived":
            filters.append(col(PromptSuggestion.archived_at).is_not(None))
        if locale:
            filters.append(col(SuggestionCategory.locale) == locale)
        if category_id:
            filters.append(col(PromptSuggestion.category_id) == category_id)

        statement = select(PromptSuggestion, SuggestionCategory).join(
            SuggestionCategory
        )
        if filters:
            statement = statement.where(*filters)

        count_statement = select(func.count()).select_from(statement.subquery())
        total = (await session.exec(count_statement)).one()
        result = await session.exec(
            # Available suggestions first. Postgres sorts nulls last on an
            # ascending column, which would float archived rows to the top.
            statement.order_by(
                col(SuggestionCategory.archived_at).is_(None).desc(),
                category_has_available_suggestions.desc(),
                (col(SuggestionCategory.locale) == "fr").desc(),
                col(SuggestionCategory.locale),
                col(SuggestionCategory.display_order),
                nulls_first(col(PromptSuggestion.archived_at)),
                col(PromptSuggestion.updated_at).desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        categories_result = await session.exec(
            select(SuggestionCategory).order_by(
                col(SuggestionCategory.archived_at).is_(None).desc(),
                category_has_available_suggestions.desc(),
                (col(SuggestionCategory.locale) == "fr").desc(),
                col(SuggestionCategory.locale),
                col(SuggestionCategory.display_order),
            )
        )
        suggestion_counts_result = await session.exec(
            select(
                PromptSuggestion.category_id, func.count(col(PromptSuggestion.id))
            ).group_by(col(PromptSuggestion.category_id))
        )
        suggestion_counts = dict(suggestion_counts_result.all())
        available_suggestion_counts_result = await session.exec(
            select(
                PromptSuggestion.category_id, func.count(col(PromptSuggestion.id))
            )
            .where(col(PromptSuggestion.archived_at).is_(None))
            .group_by(col(PromptSuggestion.category_id))
        )
        available_suggestion_counts = dict(available_suggestion_counts_result.all())
        categories = categories_result.all()
        return (
            [
                _to_admin_suggestion(suggestion, category)
                for suggestion, category in result.all()
            ],
            total,
            [
                _to_admin_category(
                    category,
                    suggestion_count=suggestion_counts.get(category.id, 0),
                    available_suggestion_count=available_suggestion_counts.get(
                        category.id, 0
                    ),
                )
                for category in categories
            ],
        )


async def create_suggestion(
    data: SuggestionCreate, *, created_by: uuid.UUID
) -> AdminSuggestion:
    async with get_session() as session:
        category = await session.get(SuggestionCategory, data.category_id)
        if category is None:
            raise SuggestionCategoryNotFoundError()
        existing = await session.exec(
            select(PromptSuggestion).where(
                PromptSuggestion.category_id == data.category_id,
                PromptSuggestion.text == data.text,
            )
        )
        if existing.first() is not None:
            raise SuggestionAlreadyExistsError()

        suggestion = PromptSuggestion(
            category_id=data.category_id,
            text=data.text,
            created_by=created_by,
        )
        session.add(suggestion)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise SuggestionAlreadyExistsError() from error
        invalidate_cache(REDIS_SUGGESTIONS_KEY)
        await session.refresh(suggestion)
        await session.refresh(category)
        return _to_admin_suggestion(suggestion, category)


def _category_key(title: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", title)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:100]


async def create_suggestion_category(
    data: SuggestionCategoryCreate,
) -> AdminSuggestionCategory:
    key = _category_key(data.title)
    if not key:
        raise SuggestionCategoryTitleUnusableError()

    async with get_session() as session:
        existing = await session.exec(
            select(SuggestionCategory).where(
                SuggestionCategory.locale == data.locale,
                SuggestionCategory.key == key,
            )
        )
        if existing.first() is not None:
            raise SuggestionCategoryAlreadyExistsError()

        max_order = (
            await session.exec(
                select(func.max(SuggestionCategory.display_order)).where(
                    SuggestionCategory.locale == data.locale
                )
            )
        ).one()
        category = SuggestionCategory(
            locale=data.locale,
            key=key,
            title=data.title,
            description=data.description,
            icon=data.icon,
            tooltip=data.tooltip,
            display_order=0 if max_order is None else max_order + 1,
        )
        session.add(category)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise SuggestionCategoryAlreadyExistsError() from error
        invalidate_cache(REDIS_SUGGESTIONS_KEY)
        await session.refresh(category)
        return _to_admin_category(category)


async def delete_suggestion_category(category_id: uuid.UUID) -> None:
    async with get_session() as session:
        category = await session.get(SuggestionCategory, category_id)
        if category is None:
            raise SuggestionCategoryNotFoundError()

        suggestion_count = (
            await session.exec(
                select(func.count(col(PromptSuggestion.id))).where(
                    col(PromptSuggestion.category_id) == category_id
                )
            )
        ).one()
        if suggestion_count:
            raise SuggestionCategoryNotEmptyError()

        await session.delete(category)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise SuggestionCategoryNotEmptyError() from error
        invalidate_cache(REDIS_SUGGESTIONS_KEY)


async def set_suggestion_archived(
    suggestion_id: uuid.UUID, *, archived: bool, updated_by: uuid.UUID
) -> AdminSuggestion:
    async with get_session() as session:
        suggestion = await session.get(PromptSuggestion, suggestion_id)
        if suggestion is None:
            raise SuggestionNotFoundError()
        category = await session.get(SuggestionCategory, suggestion.category_id)
        if category is None:
            raise SuggestionCategoryNotFoundError()

        now = datetime.now()
        suggestion.archived_at = now if archived else None
        suggestion.archived_by = updated_by if archived else None
        suggestion.updated_at = now
        session.add(suggestion)
        await session.commit()
        invalidate_cache(REDIS_SUGGESTIONS_KEY)
        await session.refresh(suggestion)
        await session.refresh(category)
        return _to_admin_suggestion(suggestion, category)


async def set_suggestion_category_archived(
    category_id: uuid.UUID, *, archived: bool, updated_by: uuid.UUID
) -> AdminSuggestionCategory:
    """Archive or restore a category without changing individual suggestions."""
    async with get_session() as session:
        category = await session.get(SuggestionCategory, category_id)
        if category is None:
            raise SuggestionCategoryNotFoundError()

        now = datetime.now()
        category.archived_at = now if archived else None
        category.archived_by = updated_by if archived else None
        session.add(category)
        await session.commit()
        invalidate_cache(REDIS_SUGGESTIONS_KEY)
        await session.refresh(category)

        suggestion_count = (
            await session.exec(
                select(func.count(col(PromptSuggestion.id))).where(
                    col(PromptSuggestion.category_id) == category_id
                )
            )
        ).one()
        available_suggestion_count = (
            await session.exec(
                select(func.count(col(PromptSuggestion.id))).where(
                    col(PromptSuggestion.category_id) == category_id,
                    col(PromptSuggestion.archived_at).is_(None),
                )
            )
        ).one()
        return _to_admin_category(
            category,
            suggestion_count=suggestion_count,
            available_suggestion_count=available_suggestion_count,
        )
