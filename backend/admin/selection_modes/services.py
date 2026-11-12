import random
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.admin.selection_modes.models import PreviewLLM, SelectionModePreview
from backend.arena.tools import get_offered_tools
from backend.errors import NoValidPairError
from backend.llms.data import LLMsData, get_llms_data
from backend.llms.selection import (
    ModeRules,
    ToolsOnOffer,
    draw_pair,
    needs_ranking,
    pools,
    viability,
)
from backend.utils.countries import get_ranking
from backend.utils.locale import get_locales_settings
from utils.database.models import (
    SelectionMode,
    SelectionModeAdmin,
    SelectionModeBase,
    SelectionModeUpsert,
    Tool,
)
from utils.database.session import get_session
from utils.ranking.compute import RankingResult
from utils.storage.redis import REDIS_SELECTION_MODES_KEY, invalidate_cache

SAMPLE_DRAWS = 5


class ModeNotFoundError(LookupError):
    pass


class ModeKeyTakenError(ValueError):
    pass


class ModeKeyImmutableError(ValueError):
    """A comparison's mode must keep meaning what it meant when it was drawn."""


class MissingDefaultLabelError(ValueError):
    """The arena falls back to the instance's default language, so a mode
    must have a label in it."""


class CannotRemoveLastModeError(ValueError):
    """The arena needs at least one mode to draw from."""


class DefaultModeChangedError(ValueError):
    """Another admin made a different mode the default at the same moment."""


# The partial unique index that allows a single default mode.
ONE_DEFAULT_INDEX = "ix_selection_mode_one_default"


async def _tools(session: AsyncSession) -> ToolsOnOffer:
    known = (await session.exec(select(Tool.key))).all()
    offered = [tool.key for tool in await get_offered_tools()]
    return ToolsOnOffer(known=set(known), offered=set(offered))


def _ranking(modes: Sequence[ModeRules]) -> RankingResult | None:
    return get_ranking() if any(needs_ranking(mode) for mode in modes) else None


def _to_admin(
    row: SelectionMode,
    llms_data: LLMsData,
    ranking: RankingResult | None,
    tools: ToolsOnOffer,
) -> SelectionModeAdmin:
    mode = SelectionModeBase.model_validate(row)
    return SelectionModeAdmin(
        **dict(mode), viability=viability(mode, llms_data, ranking, tools)
    )


async def _rows(session: AsyncSession) -> list[SelectionMode]:
    rows = await session.exec(
        select(SelectionMode).order_by(
            col(SelectionMode.position), col(SelectionMode.created_at)
        )
    )
    return list(rows.all())


async def list_modes() -> list[SelectionModeAdmin]:
    async with get_session() as session:
        rows = await _rows(session)
        modes = [SelectionModeBase.model_validate(row) for row in rows]
        llms_data = await get_llms_data()
        ranking = _ranking(modes)
        tools = await _tools(session)
        return [_to_admin(row, llms_data, ranking, tools) for row in rows]


async def _admin(row: SelectionMode, session: AsyncSession) -> SelectionModeAdmin:
    mode = SelectionModeBase.model_validate(row)
    return _to_admin(
        row, await get_llms_data(), _ranking([mode]), await _tools(session)
    )


async def _check_label(body: SelectionModeUpsert) -> None:
    if (await get_locales_settings()).default not in body.label:
        raise MissingDefaultLabelError()


async def _settle_default(
    session: AsyncSession, chosen: SelectionMode | None = None
) -> None:
    """
    Keep exactly one enabled mode the default: `chosen` when given and
    enabled, else the one already marked, else the first enabled one. The old
    default is cleared and flushed before the new one is set, so the unique
    index on the default never sees two at once.
    """
    rows = await _rows(session)
    enabled = [row for row in rows if row.enabled]
    if chosen is not None and chosen.enabled:
        keep: SelectionMode | None = chosen
    else:
        keep = next((row for row in enabled if row.is_default), None) or next(
            iter(enabled), None
        )
    for row in rows:
        if row.is_default and row is not keep:
            row.is_default = False
            session.add(row)
    await session.flush()
    if keep is not None and not keep.is_default:
        keep.is_default = True
        session.add(keep)
        try:
            await session.flush()
        except IntegrityError as e:
            # Rows read before another admin's default was committed.
            if ONE_DEFAULT_INDEX in str(e.orig):
                raise DefaultModeChangedError() from e
            raise


async def _commit(session: AsyncSession) -> None:
    await session.commit()
    invalidate_cache(REDIS_SELECTION_MODES_KEY)


async def create_mode(body: SelectionModeUpsert) -> SelectionModeAdmin:
    await _check_label(body)
    async with get_session() as session:
        if (
            await session.exec(
                select(SelectionMode).where(SelectionMode.key == body.key)
            )
        ).first():
            raise ModeKeyTakenError()
        rows = await _rows(session)
        row = SelectionMode.model_validate(
            body.model_dump(exclude={"id", "created_at", "updated_at", "position"})
        )
        # New modes go to the end of the menu; the order has its own route.
        row.position = max((r.position for r in rows), default=-1) + 1
        # Set once the old default is cleared, see _settle_default.
        wants_default, row.is_default = row.is_default, False
        session.add(row)
        try:
            await session.flush()
        except IntegrityError as e:
            raise ModeKeyTakenError() from e
        await _settle_default(session, row if wants_default else None)
        await _commit(session)
        await session.refresh(row)
        return await _admin(row, session)


async def _get(mode_id: UUID, session: AsyncSession) -> SelectionMode:
    row = await session.get(SelectionMode, mode_id)
    if row is None:
        raise ModeNotFoundError()
    return row


async def _is_last_enabled(row: SelectionMode, session: AsyncSession) -> bool:
    if not row.enabled:
        return False
    return not any(
        other.enabled and other.id != row.id for other in await _rows(session)
    )


async def update_mode(mode_id: UUID, body: SelectionModeUpsert) -> SelectionModeAdmin:
    async with get_session() as session:
        row = await _get(mode_id, session)
        if body.key != row.key:
            raise ModeKeyImmutableError()
        await _check_label(body)
        if not body.enabled and await _is_last_enabled(row, session):
            raise CannotRemoveLastModeError()
        row.sqlmodel_update(
            body.model_dump(
                exclude={
                    "id",
                    "key",
                    "created_at",
                    "updated_at",
                    "position",
                    "is_default",
                }
            )
        )
        row.updated_at = datetime.now()
        session.add(row)
        await _settle_default(session, row if body.is_default else None)
        await _commit(session)
        await session.refresh(row)
        return await _admin(row, session)


async def delete_mode(mode_id: UUID) -> None:
    async with get_session() as session:
        row = await _get(mode_id, session)
        if await _is_last_enabled(row, session):
            raise CannotRemoveLastModeError()
        await session.delete(row)
        await session.flush()
        await _settle_default(session)
        await _commit(session)


async def reorder_modes(ids: list[UUID]) -> None:
    """Put the given modes first, in that order; any left out follow."""
    async with get_session() as session:
        rows = await _rows(session)
        by_id = {row.id: row for row in rows}
        if unknown := [mode_id for mode_id in ids if mode_id not in by_id]:
            raise ModeNotFoundError(unknown)
        ordered = [by_id[mode_id] for mode_id in dict.fromkeys(ids)]
        ordered += [row for row in rows if row.id not in set(ids)]
        for position, row in enumerate(ordered):
            if row.position != position:
                row.position = position
                session.add(row)
        await _commit(session)


async def preview_mode(mode: ModeRules) -> SelectionModePreview:
    """What a mode being edited would draw, computed the way the arena does."""
    llms_data = await get_llms_data()
    ranking = _ranking([mode])
    pool_a, pool_b = pools(mode, llms_data, ranking)

    enabled = llms_data.enabled

    def describe(llm_id: UUID) -> PreviewLLM:
        llm = enabled[llm_id]
        return PreviewLLM(
            id=llm.id, name=llm.name, lab=llm.lab.name, arena_tools=llm.arena_tools
        )

    async with get_session() as session:
        tools = await _tools(session)

    draws = []
    rng = random.Random()
    in_a, in_b = set(pool_a), set(pool_b)
    for _ in range(SAMPLE_DRAWS):
        try:
            a, b = draw_pair(mode, llms_data, ranking=ranking, rng=rng)
        except NoValidPairError:
            break
        # The draw swaps sides at random; the admin reads pool A's model first.
        if not (a in in_a and b in in_b):
            a, b = b, a
        draws.append((describe(a), describe(b)))

    return SelectionModePreview(
        viability=viability(mode, llms_data, ranking, tools),
        pool_a=[describe(llm_id) for llm_id in pool_a],
        pool_b=[describe(llm_id) for llm_id in pool_b],
        sample_draws=draws,
    )
