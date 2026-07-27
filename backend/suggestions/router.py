from fastapi import APIRouter, Query

from backend.suggestions.services import list_public_suggestions
from utils.database.models.suggestion import (
    PublicSuggestionsResponse,
    SuggestionLocale,
)

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("", response_model=PublicSuggestionsResponse)
async def get_suggestions(
    locale: SuggestionLocale = Query(default="fr"),
) -> PublicSuggestionsResponse:
    return await list_public_suggestions(locale)
