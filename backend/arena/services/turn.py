import uuid

from linkup import LinkupSearchTextResult

from backend.arena.services.comparison import read_comparison
from backend.arena.services.utils import get_item
from utils.database.models import (
    ComparisonRead,
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


async def add_turn(
    comparison_id: uuid.UUID,
    prompt: str,
    web_search_results: list[LinkupSearchTextResult] | None = None,
) -> tuple[ComparisonRead, TurnRead]:
    async with get_session() as session:
        db_turn = Turn.model_validate(
            TurnCreate(
                comparison_id=comparison_id,
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
        db_turn = await get_item(Turn, id, session)
        db_turn.llm_msg_a = LLMMessage.model_validate(llm_msg_a)
        db_turn.llm_msg_b = LLMMessage.model_validate(llm_msg_b)
        session.add(db_turn)
        await session.commit()


async def update_turn_vote(
    id: uuid.UUID, vote: TurnVoteChoice | TurnVoteAnnotate
) -> None:
    async with get_session() as session:
        db_turn = await get_item(Turn, id, session)
        data = (
            {f"{k}_{vote.pos}": v for k, v in vote.model_dump().items()}
            if isinstance(vote, TurnVoteAnnotate)
            else vote.model_dump()
        )
        db_turn.sqlmodel_update(data)
        session.add(db_turn)
        await session.commit()
