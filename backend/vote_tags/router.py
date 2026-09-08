from fastapi import APIRouter, Query

from backend.vote_tags.services import list_public_vote_tags
from utils.database.models.vote_tag import PublicVoteTagsResponse

router = APIRouter(prefix="/vote-tags", tags=["vote-tags"])


@router.get("", response_model=PublicVoteTagsResponse)
async def get_vote_tags(locale: str = Query(default="fr")) -> PublicVoteTagsResponse:
    return await list_public_vote_tags(locale)
