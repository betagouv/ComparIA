import uuid
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import SQLModel

from backend.auth.dependencies import RequiredAdmin
from backend.suggestions.services import (
    SuggestionAlreadyExistsError,
    SuggestionCategoryAlreadyExistsError,
    SuggestionCategoryNotFoundError,
    SuggestionNotFoundError,
    create_suggestion,
    create_suggestion_category,
    list_admin_suggestions,
    set_suggestion_archived,
)
from utils.database.models.suggestion import (
    AdminSuggestion,
    AdminSuggestionCategory,
    SuggestionArchiveUpdate,
    SuggestionCategoryCreate,
    SuggestionCreate,
    SuggestionLocale,
)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


class AdminSuggestionsPage(SQLModel):
    items: list[AdminSuggestion]
    total: int
    page: int
    page_size: int
    categories: list[AdminSuggestionCategory]


@router.get("", response_model=AdminSuggestionsPage)
async def get_suggestions(
    search: str | None = Query(default=None, max_length=4_000),
    status_filter: Literal["available", "archived"] | None = Query(
        default=None, alias="status"
    ),
    locale: SuggestionLocale | None = Query(default=None),
    category_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> AdminSuggestionsPage:
    items, total, categories = await list_admin_suggestions(
        search=search,
        status=status_filter,
        locale=locale,
        category_id=category_id,
        page=page,
        page_size=page_size,
    )
    return AdminSuggestionsPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        categories=categories,
    )


@router.post("", response_model=AdminSuggestion, status_code=status.HTTP_201_CREATED)
async def add_suggestion(
    body: SuggestionCreate, current_user: RequiredAdmin
) -> AdminSuggestion:
    try:
        return await create_suggestion(body, created_by=current_user.id)
    except SuggestionCategoryNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    except SuggestionAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A suggestion with this text already exists in this category",
        )


@router.post(
    "/categories",
    response_model=AdminSuggestionCategory,
    status_code=status.HTTP_201_CREATED,
)
async def add_suggestion_category(
    body: SuggestionCategoryCreate, current_user: RequiredAdmin
) -> AdminSuggestionCategory:
    try:
        return await create_suggestion_category(body)
    except SuggestionCategoryAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this title already exists for this locale",
        )


@router.patch("/{suggestion_id}", response_model=AdminSuggestion)
async def patch_suggestion(
    suggestion_id: uuid.UUID,
    body: SuggestionArchiveUpdate,
    current_user: RequiredAdmin,
) -> AdminSuggestion:
    try:
        return await set_suggestion_archived(
            suggestion_id, archived=body.archived, updated_by=current_user.id
        )
    except SuggestionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Suggestion not found"
        )
