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
    from uuid import UUID

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
    """Upsert an endpoint, leaving its key alone unless a new one is given.

    The admin panel is no longer told the key, so a form round trip carries an
    empty one. Writing that through would silently disable every LLM on the
    endpoint. Clearing a key is `clear_llm_endpoint_api_key`, on purpose.
    """
    if not endpoint.api_key and endpoint.id:
        stored = await session.get(LLMEndpoint, endpoint.id)
        if stored:
            endpoint = endpoint.model_copy(update={"api_key": stored.api_key})

    return await _upsert_item(LLMEndpoint, endpoint, session, commit)


async def clear_llm_endpoint_api_key(
    endpoint_id: "UUID", session: "AsyncSession"
) -> LLMEndpoint | None:
    """Drop the stored key. Every LLM on this endpoint stops being served."""
    endpoint = await session.get(LLMEndpoint, endpoint_id)
    if not endpoint:
        return None

    endpoint.api_key = None
    session.add(endpoint)
    await session.commit()
    await session.refresh(endpoint)
    logger.info(f"Cleared api_key of LLMEndpoint '{endpoint_id}'")
    return endpoint


async def upsert_llm_data(
    llm: LLMDataUpsert, session: "AsyncSession", commit: bool = True
) -> LLMData:
    return await _upsert_item(LLMData, llm, session, commit)
