import logging
from typing import Any

from sqlmodel import col, select, union

from utils.database.models import Comparison
from utils.database.session import get_session
from utils.logger import configure_logger
from utils.models.organisations import LLMS_RAW_DATA_FILE
from utils.utils import ROOT_DIR

from .compute import RankingResult

logger = configure_logger(logging.getLogger("ranking.monitoring"))


async def get_conversations_llm_ids() -> set[str]:
    """Get distinct model IDs from the conversations table."""
    try:
        async with get_session() as session:
            results = await session.exec(
                union(
                    select(col(Comparison.llm_id_a).label("llm_id")).distinct(),
                    select(col(Comparison.llm_id_b).label("llm_id")).distinct(),
                )
            )
            return set([result[0] for result in results.all()])
    except Exception as e:
        logger.error(f"Failed to fetch distinct model IDs: {e}")
        raise e


async def monitor(llms: dict[str, Any], data: RankingResult):
    """
    Warn about missing llms definitions, ranking or preferences data
    """

    llm_ids = set(llms.keys())
    db_llm_ids = await get_conversations_llm_ids()
    new_llm_ids = set([id_ for id_ in llm_ids if llms[id_]["new"]])
    archived_llm_ids = set(
        [id_ for id_ in llm_ids if llms[id_]["status"] == "archived"]
    )
    in_db_but_not_in_list = db_llm_ids.difference(llm_ids)

    if in_db_but_not_in_list:
        logger.error(
            f"There is LLMs names in DB but not in '{LLMS_RAW_DATA_FILE.relative_to(ROOT_DIR)}': {in_db_but_not_in_list}"
        )

    for kind in ("rankings", "preferences"):
        data_llm_ids = set(getattr(data, kind).keys())

        if no_llm_for_data_ids := data_llm_ids.difference(llm_ids):
            # There is data for an LLM but its id cannot be found in LLM definitions
            # Can happen if we changed its id
            logger.error(
                f"There is '{kind}' data for LLMs that are not defined in '{LLMS_RAW_DATA_FILE.relative_to(ROOT_DIR)}': {no_llm_for_data_ids}"
            )
        if no_data_ids := archived_llm_ids.difference(data_llm_ids):
            # Can't find data for an archived LLM, maybe we could drop it from our list since we have no data at all
            logger.warning(
                f"There is no '{kind}' data for archived LLMs: {no_data_ids}"
            )
        if no_data_ids := (llm_ids - new_llm_ids - archived_llm_ids).difference(
            data_llm_ids
        ):
            # Can't find data for an LLM that is not new or archived, is it too soon? Is there a problem with its endpoint?
            logger.warning(
                f"There is no '{kind}' data for LLMs (excepting new and archived ones): {no_data_ids}"
            )

        # Try to find if there's some LLMs that do not ends up in dataset data
        if in_db_but_no_data_ids := in_db_but_not_in_list.difference(data_llm_ids):
            logger.error(
                f"LLMs are in db but not in '{kind}' data: {in_db_but_no_data_ids}"
            )
