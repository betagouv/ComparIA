import logging
from pathlib import Path

from pydantic import FilePath

from utils.database.session import get_session
from utils.llms.data import LLMImportData, get_llms_data
from utils.llms.services import (
    upsert_llm,
    upsert_llm_endpoint,
    upsert_llm_lab,
    upsert_llm_license,
)
from utils.utils import DEFAULT_LLM_DATA_PATH, read_json, write_json

logger = logging.getLogger("comparia.llms")


async def llms_import(
    file: FilePath = DEFAULT_LLM_DATA_PATH,
) -> None:
    """
    Add or update LLMs, licenses and labs database data from JSON file.
    """
    data = read_json(file, LLMImportData)

    async with get_session() as session:
        for endpoint in data.endpoints:
            await upsert_llm_endpoint(endpoint, session)

        for license in data.licenses:
            await upsert_llm_license(license, session)

        for lab in data.labs:
            await upsert_llm_lab(lab, session)

        for llm in data.llms:
            await upsert_llm(llm, session)


async def llms_export(path: Path = Path("./llms_data.json")) -> None:
    """
    Export LLMs, licenses and labs database data to a JSON file.
    """
    data = await get_llms_data()
    write_json(DEFAULT_LLM_DATA_PATH, data, sort_keys=True)
