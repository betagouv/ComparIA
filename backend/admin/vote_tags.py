import uuid

from fastapi import APIRouter, HTTPException, status

from backend.auth.dependencies import RequiredAdmin
from backend.vote_tags.services import (
    ReservedVoteTagError,
    VoteTagAlreadyExistsError,
    VoteTagInUseError,
    VoteTagLabelUnusableError,
    VoteTagNotFoundError,
    VoteTagOrderMismatchError,
    create_vote_tag,
    delete_vote_tag,
    list_admin_vote_tags,
    reorder_vote_tags,
    set_vote_tag_archived,
    update_vote_tag,
)
from utils.database.models.vote_tag import (
    AdminVoteTag,
    AdminVoteTagsResponse,
    VoteTagArchiveUpdate,
    VoteTagCreate,
    VoteTagOrder,
    VoteTagUpdate,
)

router = APIRouter(prefix="/vote-tags", tags=["vote-tags"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Vote tag not found"
)
_RESERVED = HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail="A tag shipped with the platform cannot be renamed or deleted",
)


@router.get("", response_model=AdminVoteTagsResponse)
async def get_vote_tags() -> AdminVoteTagsResponse:
    return AdminVoteTagsResponse(tags=await list_admin_vote_tags())


@router.post("", response_model=AdminVoteTag, status_code=status.HTTP_201_CREATED)
async def add_vote_tag(
    body: VoteTagCreate, current_user: RequiredAdmin
) -> AdminVoteTag:
    try:
        return await create_vote_tag(body)
    except VoteTagLabelUnusableError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A label must contain at least one letter or digit",
        )
    except VoteTagAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tag with this label already exists",
        )


@router.put("/order", response_model=AdminVoteTagsResponse)
async def set_vote_tag_order(
    body: VoteTagOrder, current_user: RequiredAdmin
) -> AdminVoteTagsResponse:
    try:
        return AdminVoteTagsResponse(tags=await reorder_vote_tags(body.sign, body.ids))
    except VoteTagOrderMismatchError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The order has to list every tag on this side, and nothing else",
        )


@router.put("/{tag_id}", response_model=AdminVoteTag)
async def edit_vote_tag(
    tag_id: uuid.UUID, body: VoteTagUpdate, current_user: RequiredAdmin
) -> AdminVoteTag:
    try:
        return await update_vote_tag(tag_id, body)
    except VoteTagNotFoundError:
        raise _NOT_FOUND
    except ReservedVoteTagError:
        raise _RESERVED


@router.patch("/{tag_id}", response_model=AdminVoteTag)
async def patch_vote_tag(
    tag_id: uuid.UUID, body: VoteTagArchiveUpdate, current_user: RequiredAdmin
) -> AdminVoteTag:
    try:
        return await set_vote_tag_archived(
            tag_id, archived=body.archived, updated_by=current_user.id
        )
    except VoteTagNotFoundError:
        raise _NOT_FOUND


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vote_tag(tag_id: uuid.UUID, current_user: RequiredAdmin) -> None:
    try:
        await delete_vote_tag(tag_id, updated_by=current_user.id)
    except VoteTagNotFoundError:
        raise _NOT_FOUND
    except ReservedVoteTagError:
        raise _RESERVED
    except VoteTagInUseError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Votes already carry this tag, archive it instead",
        )
