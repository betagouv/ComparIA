from fastapi import APIRouter

from backend.suggestions.services import list_public_suggestions
from backend.utils.locale import LocaleQueryStrict
from utils.database.models.suggestion import PublicSuggestionsResponse

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


@router.get("", response_model=PublicSuggestionsResponse)
async def get_suggestions(locale: LocaleQueryStrict) -> PublicSuggestionsResponse:
    return await list_public_suggestions(locale)
