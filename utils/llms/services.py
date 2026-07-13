import logging
from typing import TYPE_CHECKING, TypeVar

from utils.database.models.llms import (
    LLMData,
    LLMDataUpsert,
    LLMEndpoint,
    LLMEndpointUpsert,
    LLMLab,
    LLMLabUpsert,
    LLMLicense,
    LLMLicenseUpsert,
)

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

logger = logging.getLogger("comparia.db")

T = TypeVar("T", bound=LLMLicense | LLMLab | LLMEndpoint | LLMData)
TD = TypeVar(
    "T", bound=LLMLicenseUpsert | LLMLabUpsert | LLMEndpointUpsert | LLMDataUpsert
)


async def _upsert_item(
    item_class: type[T], item: TD, session: "AsyncSession", commit: bool
) -> T:
    base_msg = f"'{item_class.__name__}' with id: '{item.id}'"

    try:
        db_item = await session.get(item_class, item.id)

        if db_item:
            logger.debug(f"Updating {base_msg}…")
            data = item.model_dump(exclude={"id", "created_at"})
            db_item.sqlmodel_update(data)
        else:
            logger.debug(f"Adding {base_msg}…")
            db_item = item_class.model_validate(item)

        session.add(db_item)

        if commit:
            await session.commit()
            logger.info(f"Successfully added/updated {base_msg}")

        return db_item
    except Exception as e:
        logger.error(f"Error adding/updating {base_msg}: {e}")
        raise


async def upsert_llm_license(
    license: LLMLicenseUpsert, session: "AsyncSession", commit: bool = True
) -> LLMLicense:
    return await _upsert_item(LLMLicense, license, session, commit)


async def upsert_llm_lab(
    lab: LLMLabUpsert, session: "AsyncSession", commit: bool = True
) -> LLMLab:
    return await _upsert_item(LLMLab, lab, session, commit)


async def upsert_llm_endpoint(
    endpoint: LLMEndpointUpsert, session: "AsyncSession", commit: bool = True
) -> LLMEndpoint:
    return await _upsert_item(LLMEndpoint, endpoint, session, commit)


async def upsert_llm(
    llm: LLMDataUpsert, session: "AsyncSession", commit: bool = True
) -> LLMData:
    return await _upsert_item(LLMData, llm, session, commit)
