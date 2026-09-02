from typing import cast, get_args

from fastapi import APIRouter, Query

from backend.suggestions.services import list_public_suggestions
from utils.database.models.suggestion import (
    PublicSuggestionsResponse,
    SuggestionLocale,
)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

_SUPPORTED_LOCALES = frozenset(get_args(SuggestionLocale))


@router.get("", response_model=PublicSuggestionsResponse)
async def get_suggestions(
    locale: str = Query(default="fr"),
) -> PublicSuggestionsResponse:
    # The site ships more locales than the ones with curated content. An
    # unsupported locale means "nothing to show", not a bad request.
    if locale not in _SUPPORTED_LOCALES:
        return PublicSuggestionsResponse(categories=[])
    return await list_public_suggestions(cast(SuggestionLocale, locale))
