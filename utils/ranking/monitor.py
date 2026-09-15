import logging
from datetime import datetime
from uuid import UUID

from sqlmodel import select

from utils.database.models.llms import LLMData
from utils.database.session import get_session
from utils.logger import configure_logger

from .compute import RankingResult

logger = configure_logger(logging.getLogger("ranking.monitoring"))


async def get_llms_data() -> list[LLMData]:
    """Load raw LLMs data from database."""
    try:
        async with get_session() as session:
            return (await session.exec(select(LLMData))).all()
    except Exception as e:
        logger.error(f"Failed to query LLMs data: {e}")
        raise e


async def monitor(data: RankingResult):
    """
    Warn about available or missing ranking or preference data
    """

    today = datetime.now()
    llms = await get_llms_data()
    llms_ids = set([llm.id for llm in llms])
    new_llm_ids = set([llm.id for llm in llms if (today - llm.created_at).days <= 30])
    archived_llm_ids = set([llm.id for llm in llms if llm.status == "archived"])
    disabled_llm_ids = set([llm.id for llm in llms if llm.status == "disabled"])
    enabled_llm_ids = llms_ids - archived_llm_ids - disabled_llm_ids

    ids_to_human_id_map = {llm.id: llm.human_id for llm in llms}

    def list_llms(ids: set[UUID]) -> str:
        return f"\n{"\n".join(f" - {id}: '{ids_to_human_id_map[id]}'" for id in ids)}"

    for kind in ("rankings",):  # "preferences"
        data_llm_ids = set(getattr(data, kind).keys())

        if ids := archived_llm_ids.difference(data_llm_ids):
            # Can't find data for an archived LLM
            logger.warning(
                f"There is no '{kind}' data for 'archived' LLMs. Consider deleting or disabling it instead to avoid displaying it in LLM list:{list_llms(ids)}"
            )
        if ids := disabled_llm_ids.difference(data_llm_ids):
            # There is data for a disabled LLM that is therefore not displayed
            logger.warning(
                f"There is '{kind}' data for 'disabled' LLMs. Consider archiving it instead to display it in LLM list and ranking:{list_llms(ids)}"
            )
        if ids := (enabled_llm_ids - new_llm_ids).difference(data_llm_ids):
            # Can't find data for an LLM that is enabled and available since a month.
            logger.warning(
                f"There is no '{kind}' data for 'enabled' LLMs (excepting new ones). Maybe there is a problem with its endpoint?{list_llms(ids)}"
            )
