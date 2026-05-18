import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Literal, Sequence, TypedDict, cast, get_args

from sqlalchemy import text
from sqlalchemy.orm import selectinload
from sqlmodel import col, select

from backend.arena.models import BotPos
from utils.utils import db_connection

from .models import Comparison, Turn
from .models.comparison import ArchivedReason
from .session import get_session

TableName = Literal["conversations", "votes", "reactions"]
TABLE_NAMES: tuple[TableName, ...] = get_args(TableName)


logger = logging.getLogger("comparia.db")


async def get_db_comparisons_stream(
    filters: list[Any] | None = None,
) -> AsyncGenerator[Comparison]:
    async with get_session() as session:
        query = select(Comparison).options(
            selectinload(Comparison.turns).options(
                selectinload(Turn.user_msg),
                selectinload(Turn.llm_msg_a),
                selectinload(Turn.llm_msg_b),
            ),
            selectinload(Comparison.system_msg_a),
            selectinload(Comparison.system_msg_b),
        )
        if filters:
            for _filter in filters:
                query = query.filter(_filter)

        query = query.order_by(col(Comparison.created_at))
        logger.debug(f"Will query Comparison with:\n{query}")
        stream = await session.stream(query.execution_options(yield_per=1000))

        async for (s,) in stream:
            yield s


def archive(
    table_name: TableName,
    ids: Sequence[str | int],
    archived_reason: ArchivedReason,
    archived_at: datetime,
    id_key: str = "conversation_pair_id",
    commit: bool = False,
) -> int:
    """
    Archive given table related ids objects with reason and archive date.
    Log only by default what would have been archive, set 'commit' to True to
    actually archive those.
    """
    query = """
        UPDATE {table_name} 
        SET 
            archived = TRUE,
            archived_reason = '{archived_reason}',
            archived_at = '{archived_at}'
        WHERE
            {id_key} IN ({ids});
    """.format(
        table_name=table_name,
        archived_reason=archived_reason,
        archived_at=archived_at,
        ids=", ".join([f"'{id}'" for id in ids]),
        id_key=id_key,
    )

    with db_connection() as conn:
        results = conn.execute(text(query))

        if commit:
            conn.commit()
            logger.info(
                f"Successfully archived {results.rowcount} '{archived_reason}' {table_name}."
            )
        else:
            logger.error(
                f"{results.rowcount} '{archived_reason}' {table_name} should be archived."
            )

        return results.rowcount


def reset_archived():
    """
    Reset all conversations, votes and reaction 'archived' column to NULL if FALSE.
    Used to run db linting in hard mode (reanalyzing).
    """
    query = """
        UPDATE
            {table_name}
        SET
            archived = NULL
        WHERE
            archived = FALSE
        ;
    """
    with db_connection() as conn:
        for table_name in TABLE_NAMES:
            logger.info(
                f"Resetting 'achived=FALSE' to 'archived=NULL' in {table_name}."
            )
            results = conn.execute(text(query.format(table_name=table_name)))

            conn.commit()
            logger.info(
                f"Resetted {results.rowcount} 'archived' to NULL on {table_name}."
            )


def set_not_archived(timestamp: datetime):
    """
    Set all conversations, votes and reaction 'archived' column to FALSE if NULL.
    Only affects items inserted before given timestamp.
    Used after linting to mark data as analyzed.
    """
    query = """
        UPDATE {table_name} 
        SET archived = FALSE
        WHERE archived IS NULL AND timestamp < TIMESTAMP '{timestamp}';
    """

    with db_connection() as conn:
        for table_name in TABLE_NAMES:
            logger.info(
                f"Set {table_name} 'archived' to FALSE if timestamp < {timestamp}."
            )
            results = conn.execute(
                text(query.format(table_name=table_name, timestamp=timestamp))
            )

            conn.commit()
            logger.info(f"Set {results.rowcount} 'archived' to FALSE on {table_name}.")


class RawSystemMessage(TypedDict):
    role: Literal["system"]
    content: str


class RawUserMessage(TypedDict):
    role: Literal["user"]
    content: str


class RawLLMMessage(TypedDict):
    role: Literal["assistant"]
    content: str
    reasoning_content: str | None


AnyRawMessage = RawSystemMessage | RawUserMessage | RawLLMMessage


def parse_full_conversation(
    comparison: Comparison, side: BotPos
) -> list[AnyRawMessage]:
    conversation: list[AnyRawMessage] = []

    if system_msg := getattr(comparison, f"system_msg_{side}"):
        raw_system_msg = cast(
            RawSystemMessage, system_msg.model_dump(include={"role", "content"})
        )
        conversation.append(raw_system_msg)

    for turn in comparison.turns:
        raw_user_msg = cast(
            RawUserMessage, turn.user_msg.model_dump(include={"role", "content"})
        )
        conversation.append(raw_user_msg)

        if llm_msg := getattr(turn, f"llm_msg_{side}"):
            raw_llm_msg = cast(
                RawLLMMessage,
                llm_msg.model_dump(include={"role", "content", "reasoning_content"}),
            )
            conversation.append(raw_llm_msg)

    return conversation
