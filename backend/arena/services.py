import uuid
from datetime import datetime
from typing import TYPE_CHECKING, TypeVar

from fastapi import HTTPException, status
from linkup import LinkupSearchTextResult

from backend.llms.data import get_llms_data
from utils.database.models import (
    BOT_POS,
    BotPos,
    Comparison,
    ComparisonCreate,
    ComparisonRead,
    ErrorDetails,
    LLMMessage,
    LLMMessageCreate,
    Turn,
    TurnCreate,
    TurnRead,
    TurnVoteAnnotate,
    TurnVoteChoice,
    UserMessage,
)
from utils.database.session import get_session

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession


T = TypeVar("T", bound=Comparison | Turn)


async def _get_item(item_class: type[T], id: uuid.UUID, session: "AsyncSession") -> T:
    db_item = await session.get(item_class, id)

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{item_class.__name__} not found",
        )

    return db_item


async def create_comparison(comparison: ComparisonCreate) -> ComparisonRead:
    async with get_session() as session:
        db_comparison = Comparison.model_validate(comparison)
        llms_data = (await get_llms_data()).enabled

        for pos in BOT_POS:
            if content := llms_data[getattr(comparison, f"llm_id_{pos}")].system_prompt:
                setattr(db_comparison, f"system_msg_{pos}", content)

        session.add(db_comparison)
        await session.commit()
        await session.refresh(db_comparison)

    return ComparisonRead.model_validate(db_comparison)


async def read_comparison(id: uuid.UUID) -> ComparisonRead:
    async with get_session() as session:
        db_comparison = await _get_item(Comparison, id, session)

    return ComparisonRead.model_validate(db_comparison)


async def update_comparison_llm_id(
    comparison: ComparisonRead, pos: BotPos, new_llm_id: str
) -> None:
    failing_llm_id = getattr(comparison, f"llm_id_{pos}")

    # Mutate the current ComparisonRead and TurnRead
    # Update current ComparisonRead failing LLM id
    setattr(comparison, f"llm_id_{pos}", new_llm_id)
    # Remove or add new system_msg if any
    llm = (await get_llms_data()).enabled[new_llm_id]
    system_msg = llm.system_prompt if llm.system_prompt else None
    setattr(comparison, f"system_msg_{pos}", system_msg)
    # Reset TurnRead llm_msg_* to None (no need to do it in db, it is not yet saved)
    setattr(comparison.turns[-1], f"llm_msg_{pos}", None)
    # Mutate custom selection
    if selection := comparison.custom_models_selection:
        # Filter failing model from custom_models_selection
        new_selection = tuple(
            llm_id for llm_id in selection if llm_id != failing_llm_id
        )
        comparison.custom_models_selection = (
            (new_selection[0],) if new_selection else None
        )

    # Reflect changes in db
    async with get_session() as session:
        db_comparison = await _get_item(Comparison, comparison.id, session)
        setattr(db_comparison, f"llm_id_{pos}", new_llm_id)
        setattr(db_comparison, f"system_msg_{pos}", system_msg)
        db_comparison.custom_models_selection = comparison.custom_models_selection
        db_comparison.updated_at = datetime.now()
        session.add(db_comparison)
        await session.commit()


async def update_comparison_error(
    comparison: ComparisonRead, error: ErrorDetails | None = None
) -> None:
    comparison.error = error

    async with get_session() as session:
        db_comparison = await _get_item(Comparison, comparison.id, session)
        db_comparison.error = error.model_dump() if error else None
        db_comparison.updated_at = datetime.now()
        await session.commit()


async def add_comparison_turn(
    comparison_id: uuid.UUID,
    prompt: str,
    web_search_results: list[LinkupSearchTextResult] | None = None,
    guardrail: dict | None = None,
) -> tuple[ComparisonRead, TurnRead]:
    async with get_session() as session:
        db_turn = Turn.model_validate(
            TurnCreate(
                comparison_id=comparison_id,
                guardrail=guardrail,
                user_msg=UserMessage(
                    content=prompt,
                    web_search_results=(
                        [w.model_dump() for w in web_search_results]
                        if web_search_results
                        else None
                    ),
                ),
            )
        )
        new_turn_id = db_turn.id
        session.add(db_turn)
        await session.commit()

    comparison = await read_comparison(comparison_id)

    return (comparison, next(t for t in comparison.turns if t.id == new_turn_id))


async def update_turn(
    id: uuid.UUID, llm_msg_a: LLMMessageCreate, llm_msg_b: LLMMessageCreate
) -> None:
    async with get_session() as session:
        db_turn = await _get_item(Turn, id, session)
        db_turn.llm_msg_a = LLMMessage.model_validate(llm_msg_a)
        db_turn.llm_msg_b = LLMMessage.model_validate(llm_msg_b)
        session.add(db_turn)
        await session.commit()


async def update_turn_vote(
    id: uuid.UUID, vote: TurnVoteChoice | TurnVoteAnnotate
) -> None:
    async with get_session() as session:
        db_turn = await _get_item(Turn, id, session)
        if isinstance(vote, TurnVoteAnnotate):
            data = {f"{k}_{vote.pos}": v for k, v in vote.model_dump().items()}
        else:
            # A choice vote can only be cast once (enforced in the router), so
            # this stamps the single moment the user decided.
            data = {**vote.model_dump(), "voted_at": datetime.now()}
        db_turn.sqlmodel_update(data)
        session.add(db_turn)
        await session.commit()
