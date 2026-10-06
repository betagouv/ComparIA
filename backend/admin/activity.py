import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from backend.activity.models import (
    ActivityConversation,
    ActivityConversationsPage,
    ActivityFilterOptions,
    ActivityFilters,
    ActivityOverview,
    ConversationFilters,
)
from backend.activity.services import (
    InvalidCursorError,
    QueryTimedOutError,
    get_conversation,
    get_filter_options,
    get_overview,
    list_conversations,
)
from backend.auth.dependencies import RequiredAdmin
from backend.errors import ActivityQueryTimeoutError

logger = logging.getLogger("languia")

router = APIRouter(prefix="/activity", tags=["activity"])


@contextmanager
def _timeout_as_503() -> Iterator[None]:
    try:
        yield
    except QueryTimedOutError:
        raise ActivityQueryTimeoutError()


@router.get("/filters", response_model=ActivityFilterOptions)
async def read_filter_options(refresh: bool = False) -> ActivityFilterOptions:
    with _timeout_as_503():
        return await get_filter_options(refresh)


class OverviewQuery(ActivityFilters):
    # Skips the cache, for the button next to the age of the numbers.
    refresh: bool = False


@router.get("/overview", response_model=ActivityOverview)
async def read_overview(query: Annotated[OverviewQuery, Query()]) -> ActivityOverview:
    """Counts for the period, cached a few minutes per set of filters."""
    filters = ActivityFilters(**query.model_dump(exclude={"refresh"}))
    with _timeout_as_503():
        return await get_overview(filters, query.refresh)


@router.get("/conversations", response_model=ActivityConversationsPage)
async def read_conversations(
    filters: Annotated[ConversationFilters, Query()],
) -> ActivityConversationsPage:
    """Newest first. Pages follow `next_cursor` rather than a page number, so
    the thousandth page costs what the first does."""
    with _timeout_as_503():
        try:
            return await list_conversations(filters)
        except InvalidCursorError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_cursor"
            )


@router.get("/conversations/{comparison_id}", response_model=ActivityConversation)
async def read_conversation(
    comparison_id: uuid.UUID, current_user: RequiredAdmin
) -> ActivityConversation:
    # Admins read what visitors wrote, personal data included: keep a trace of
    # who opened which conversation.
    logger.info(
        f"[ADMIN] conversation {comparison_id} opened by admin {current_user.id}"
    )
    with _timeout_as_503():
        conversation = await get_conversation(comparison_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return conversation
