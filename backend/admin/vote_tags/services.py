import re
import unicodedata
import uuid
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from utils.database.models.turn import Turn
from utils.database.models.vote_tag import (
    RESERVED_KEYS,
    AdminVoteTag,
    VoteTag,
    VoteTagCreate,
    VoteTagSign,
    VoteTagUpdate,
)
from utils.database.session import get_session
from utils.storage.redis import REDIS_VOTE_TAGS_KEY, invalidate_cache


class VoteTagNotFoundError(Exception):
    pass


class VoteTagAlreadyExistsError(Exception):
    pass


class VoteTagLabelUnusableError(Exception):
    """A label with no letters or digits leaves nothing to build a key from."""


class ReservedVoteTagError(Exception):
    """Reserved tags can be hidden and reordered, never renamed or deleted."""


class VoteTagInUseError(Exception):
    """Votes already carry this key, so it is archived rather than deleted."""


class VoteTagOrderMismatchError(Exception):
    """An order has to list every tag on the side, and nothing else."""


def _tag_key(label: str) -> str:
    normalized = (
        unicodedata.normalize("NFKD", label)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")[:100]


async def _count_usage(session, key: str) -> int:
    """
    Votes carry their tags in two JSONB arrays, one per model. 'jsonb_exists'
    reads an array of strings, so this answers "did anyone pick this tag"
    without unnesting the column.
    """
    statement = select(func.count(col(Turn.id))).where(
        or_(
            func.jsonb_exists(col(Turn.keyword_annotations_a), key),
            func.jsonb_exists(col(Turn.keyword_annotations_b), key),
        )
    )
    return (await session.exec(statement)).one()


def _to_admin_tag(tag: VoteTag, usage_count: int) -> AdminVoteTag:
    return AdminVoteTag(
        id=tag.id,
        key=tag.key,
        sign=tag.sign,
        emoji=tag.emoji,
        reserved=tag.reserved,
        labels=tag.labels,
        display_order=tag.display_order,
        archived=tag.archived_at is not None,
        usage_count=usage_count,
    )


async def list_admin_vote_tags() -> list[AdminVoteTag]:
    async with get_session() as session:
        result = await session.exec(
            select(VoteTag).order_by(col(VoteTag.sign), col(VoteTag.display_order))
        )
        tags = list(result.all())
        return [
            _to_admin_tag(tag, await _count_usage(session, tag.key)) for tag in tags
        ]


async def create_vote_tag(data: VoteTagCreate) -> AdminVoteTag:
    key = _tag_key(next(iter(data.labels.values())))
    if not key:
        raise VoteTagLabelUnusableError()
    if key in RESERVED_KEYS:
        raise VoteTagAlreadyExistsError()

    async with get_session() as session:
        max_order = (
            await session.exec(
                select(func.max(VoteTag.display_order)).where(VoteTag.sign == data.sign)
            )
        ).one()
        tag = VoteTag(
            key=key,
            sign=data.sign,
            emoji=data.emoji,
            reserved=False,
            labels=dict(data.labels),
            display_order=0 if max_order is None else max_order + 1,
        )
        session.add(tag)
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise VoteTagAlreadyExistsError() from error
        invalidate_cache(REDIS_VOTE_TAGS_KEY)
        await session.refresh(tag)
        return _to_admin_tag(tag, 0)


async def update_vote_tag(tag_id: uuid.UUID, data: VoteTagUpdate) -> AdminVoteTag:
    """
    Emoji and labels only. The key is what past votes point at, so it stays put
    however the label is corrected.
    """
    async with get_session() as session:
        tag = await session.get(VoteTag, tag_id)
        if tag is None:
            raise VoteTagNotFoundError()
        if tag.reserved:
            raise ReservedVoteTagError()

        tag.emoji = data.emoji
        tag.labels = dict(data.labels)
        tag.updated_at = datetime.now()
        session.add(tag)
        await session.commit()
        invalidate_cache(REDIS_VOTE_TAGS_KEY)
        await session.refresh(tag)
        return _to_admin_tag(tag, await _count_usage(session, tag.key))


async def set_vote_tag_archived(
    tag_id: uuid.UUID, *, archived: bool, updated_by: uuid.UUID
) -> AdminVoteTag:
    async with get_session() as session:
        tag = await session.get(VoteTag, tag_id)
        if tag is None:
            raise VoteTagNotFoundError()

        now = datetime.now()
        tag.archived_at = now if archived else None
        tag.archived_by = updated_by if archived else None
        tag.updated_at = now
        session.add(tag)
        await session.commit()
        invalidate_cache(REDIS_VOTE_TAGS_KEY)
        await session.refresh(tag)
        return _to_admin_tag(tag, await _count_usage(session, tag.key))


async def delete_vote_tag(tag_id: uuid.UUID, *, updated_by: uuid.UUID) -> None:
    """
    Deletes a tag nobody has used, so a mistyped key never reaches the export.
    Once a vote carries it the row is archived instead: the counts stay and the
    published vocabulary keeps describing it.
    """
    async with get_session() as session:
        tag = await session.get(VoteTag, tag_id)
        if tag is None:
            raise VoteTagNotFoundError()
        if tag.reserved:
            raise ReservedVoteTagError()

        if await _count_usage(session, tag.key):
            raise VoteTagInUseError()

        await session.delete(tag)
        await session.commit()
        invalidate_cache(REDIS_VOTE_TAGS_KEY)


async def reorder_vote_tags(
    sign: VoteTagSign, ids: list[uuid.UUID]
) -> list[AdminVoteTag]:
    """
    Write one side's order from the list the client sends. It has to name every
    tag on that side exactly once, so a stale page cannot drop a tag another
    admin added in the meantime.
    """
    async with get_session() as session:
        siblings = list(
            (await session.exec(select(VoteTag).where(VoteTag.sign == sign))).all()
        )
        by_id = {row.id: row for row in siblings}
        if len(ids) != len(by_id) or set(ids) != set(by_id):
            raise VoteTagOrderMismatchError()

        for position, tag_id in enumerate(ids):
            row = by_id[tag_id]
            row.display_order = position
            session.add(row)
        await session.commit()
        invalidate_cache(REDIS_VOTE_TAGS_KEY)

    return await list_admin_vote_tags()
