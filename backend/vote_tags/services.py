from sqlmodel import col, select

from backend.config import TurnChoice
from utils.database.models.utils import BotPos
from utils.database.models.vote_tag import (
    PublicVoteTag,
    PublicVoteTagsResponse,
    VoteTag,
    VoteTagSign,
)
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.storage.redis import REDIS_VOTE_TAGS_KEY, redis_cache


class UnknownVoteTagError(Exception):
    """A key that is not an active tag on this instance."""


class VoteTagSignMismatchError(Exception):
    """A negative tag on a positive vote, or the other way round."""


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
