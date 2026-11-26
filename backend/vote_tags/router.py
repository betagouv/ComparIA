from fastapi import APIRouter

from backend.utils.locale import LocaleQuery
from backend.vote_tags.services import list_public_vote_tags
from utils.database.models.vote_tag import PublicVoteTagsResponse

router = APIRouter(prefix="/vote-tags", tags=["vote-tags"])


@router.get("", response_model=PublicVoteTagsResponse)
async def get_vote_tags(locale: LocaleQuery) -> PublicVoteTagsResponse:
    return await list_public_vote_tags(locale)
