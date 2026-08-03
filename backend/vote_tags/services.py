import re
import unicodedata
import uuid
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, func, select

from backend.config import TurnChoice
from utils.database.models.turn import Turn
from utils.database.models.utils import BotPos
from utils.database.models.vote_tag import (
    RESERVED_KEYS,
    AdminVoteTag,
    PublicVoteTag,
    PublicVoteTagsResponse,
    VoteTag,
    VoteTagCreate,
    VoteTagSign,
    VoteTagUpdate,
)
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.storage.redis import REDIS_VOTE_TAGS_KEY, invalidate_cache, redis_cache


class UnknownVoteTagError(Exception):
    """A key that is not an active tag on this instance."""


class VoteTagSignMismatchError(Exception):
    """A negative tag on a positive vote, or the other way round."""


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


@redis_cache(REDIS_VOTE_TAGS_KEY)
async def get_active_vote_tags() -> list[VoteTag]:
    """
    Every tag currently offered to voters, in display order within each sign.
    Cached rather than resolved per locale: labels are a dict lookup on top of
    these rows, so one cached list serves every language.
    """
    async with get_session() as session:
        result = await session.exec(
            select(VoteTag)
            .where(col(VoteTag.archived_at).is_(None))
            .order_by(col(VoteTag.sign), col(VoteTag.display_order))
        )
        return list(result.all())


async def get_active_signs_by_key() -> dict[str, VoteTagSign]:
    return {tag.key: tag.sign for tag in await get_active_vote_tags()}


@redis_cache(REDIS_VOTE_TAGS_KEY)
async def get_all_vote_tags() -> list[VoteTag]:
    """Every tag, archived ones included, in display order within each sign."""
    async with get_session() as session:
        result = await session.exec(
            select(VoteTag).order_by(col(VoteTag.sign), col(VoteTag.display_order))
        )
        return list(result.all())


@redis_cache(REDIS_VOTE_TAGS_KEY)
async def get_all_vote_tag_signs() -> dict[str, VoteTagSign]:
    """
    Sign of every tag, archived ones included. Counting past votes needs the
    tags that are no longer offered, so this cannot filter on 'archived_at'.
    """
    async with get_session() as session:
        result = await session.exec(select(VoteTag))
        return {tag.key: tag.sign for tag in result.all()}


def expected_sign(choice: TurnChoice, pos: BotPos) -> VoteTagSign | None:
    """
    Which side of the taxonomy a voter is answering for this model. 'idk'
    skips the vote, so it takes no tags at all.
    """
    if choice == "idk":
        return None
    return "positive" if choice in ("both_good", f"{pos}_better") else "negative"


async def check_vote_tags(keys: list[str], choice: TurnChoice, pos: BotPos) -> None:
    """
    Guard the keys a vote carries. Until the taxonomy moved to the database
    this was a Literal on the column, so nothing checked the sign and a
    negative tag could land on a positive vote.
    """
    if not keys:
        return

    sign = expected_sign(choice, pos)
    if sign is None:
        raise VoteTagSignMismatchError()

    signs = await get_active_signs_by_key()
    if unknown := [key for key in keys if key not in signs]:
        raise UnknownVoteTagError(", ".join(sorted(unknown)))
    if mismatched := [key for key in keys if signs[key] != sign]:
        raise VoteTagSignMismatchError(", ".join(sorted(mismatched)))


async def _label(tag: VoteTag, locale: str) -> str | None:
    # Reserved tags are translated in the message files, so the API sends no
    # label for them and the frontend reads 'vote.choices.{sign}.{key}'.
    if tag.reserved or not tag.labels:
        return None
    if locale in tag.labels:
        return tag.labels[locale]
    default_locale = (await get_app_settings()).default_locale
    return tag.labels.get(default_locale) or next(iter(tag.labels.values()), None)


async def list_public_vote_tags(locale: str) -> PublicVoteTagsResponse:
    return PublicVoteTagsResponse(
        tags=[
            PublicVoteTag(
                key=tag.key,
                sign=tag.sign,
                emoji=tag.emoji,
                reserved=tag.reserved,
                label=await _label(tag, locale),
            )
            for tag in await get_active_vote_tags()
        ]
    )


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


async def move_vote_tag(tag_id: uuid.UUID, direction: str) -> list[AdminVoteTag]:
    """Swap a tag with its neighbour on the same side."""
    async with get_session() as session:
        tag = await session.get(VoteTag, tag_id)
        if tag is None:
            raise VoteTagNotFoundError()

        siblings = list(
            (
                await session.exec(
                    select(VoteTag)
                    .where(VoteTag.sign == tag.sign)
                    .order_by(col(VoteTag.display_order))
                )
            ).all()
        )
        index = next(i for i, row in enumerate(siblings) if row.id == tag.id)
        target = index - 1 if direction == "up" else index + 1
        if 0 <= target < len(siblings):
            # Rewrite the whole side: display_order can hold gaps or ties from
            # earlier deletions, so swapping two values is not enough.
            siblings[index], siblings[target] = siblings[target], siblings[index]
            for position, row in enumerate(siblings):
                row.display_order = position
                session.add(row)
            await session.commit()
            invalidate_cache(REDIS_VOTE_TAGS_KEY)

    return await list_admin_vote_tags()
