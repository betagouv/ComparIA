import logging
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Literal, cast

from sqlmodel import col

from ..models import Comparison
from ..models.comparison import BOT_POS, ArchivedReason, BotPos
from ..utils import RawLLMMessage, archive, get_db_comparisons_stream

logger = logging.getLogger("comparia.db")


def has_nonish_content(
    msgs: list[RawLLMMessage],
) -> tuple[Literal["all", "last", "some"], Literal["none", "empty"]] | None:
    count = len(msgs)
    are_none = [msg.get("content") is None for msg in msgs]
    are_empty = [msg.get("content") == "" for msg in msgs]
    kinds: dict[Literal["none", "empty"], list[bool]] = {
        "none": [msg.get("content") is None for msg in msgs],
        "empty": [msg.get("content") == "" for msg in msgs],
    }
    for k, nonishs in kinds.items():
        n = len([nonish for nonish in nonishs if nonish is True])
        if n == 0:
            continue
        if n == count:
            return ("all", k)
        if nonishs.index(True) == count - 1:
            return ("last", k)
        return ("some", k)

    return None


def has_model_stream_content(msgs: list[RawLLMMessage]) -> bool:
    contents = [msg.get("content", "") for msg in msgs]
    return any(
        content.startswith("ModelResponse") or "ModelResponseStream" in content
        for content in contents
    )


def get_llm_msgs(comparison: Comparison) -> dict[BotPos, list[RawLLMMessage]]:
    llm_msgs: dict[BotPos, list[RawLLMMessage]] = {"a": [], "b": []}
    for turn in comparison.turns:
        for side in BOT_POS:
            if llm_msg := getattr(turn, f"llm_msg_{side}"):
                raw_llm_msg = cast(
                    RawLLMMessage,
                    llm_msg.model_dump(
                        include={"role", "content", "reasoning_content"}
                    ),
                )
                llm_msgs[side].append(raw_llm_msg)

    return llm_msgs


async def archive_corrupted(*, commit: bool = False) -> None:
    """
    Archive comparisons with corrupted data.
    """
    logger.info("Searching for corrupted data in comparisons")
    archived_at = datetime.now()
    reasons: dict[ArchivedReason, set[uuid.UUID]] = defaultdict(lambda: set())

    async for db_comp in get_db_comparisons_stream([col(Comparison.archived) == None]):
        if db_comp.llm_id_a == db_comp.llm_id_b:
            reasons["corrupted_against_self"].add(db_comp.id)
            continue

        llm_msgs = get_llm_msgs(db_comp)

        if any(len(msgs) == 0 for msgs in llm_msgs.values()):
            reasons["corrupted_no_response"].add(db_comp.id)
            continue

        nonish_contents = [has_nonish_content(msgs) for msgs in llm_msgs.values()]
        if nonish := next((n for n in nonish_contents if n), None):
            reason = cast(
                ArchivedReason,
                f"corrupted_response_{nonish[0]}_{nonish[1]}",
            )
            reasons[reason].add(db_comp.id)
            continue

        if any(has_model_stream_content(msgs) for msgs in llm_msgs.values()):
            reasons["corrupted_model_stream"].add(db_comp.id)

    if not any(reasons.values()):
        logger.info(f"No comparisons with corrupted data found!")
        return
    for reason, ids in reasons.items():
        logger.warning(
            f"Found {len(ids)} comparisons with corrupted content: '{reason}'."
        )
        await archive(list(ids), reason, archived_at, commit=commit)
