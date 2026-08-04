import asyncio
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, select

from backend.publishing import next_run_at
from utils.database.models.publish import (
    AdminPublishDestination,
    AdminPublishDestinationsResponse,
    AdminPublishRun,
    AdminPublishStatus,
    MissingSecretError,
    PublishDestination,
    PublishDestinationUpsert,
    config_to_store,
)
from utils.database.session import get_session
from utils.database.settings import get_app_settings
from utils.dataset.publish import DestinationError, check_destination
from utils.dataset.runs import last_run

router = APIRouter(prefix="/publishing", tags=["publishing"])


def _missing_secret(exc: MissingSecretError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"'{exc.field}' is required for this kind of destination",
    )


@router.get("/status", response_model=AdminPublishStatus)
async def get_status() -> AdminPublishStatus:
    app_settings = await get_app_settings()
    run = await last_run()
    return AdminPublishStatus(
        frequency=app_settings.publish_frequency,
        hour=app_settings.publish_hour,
        timezone=app_settings.publish_timezone,
        last_run=AdminPublishRun.model_validate(run.model_dump()) if run else None,
        next_run_at=next_run_at(app_settings, datetime.now(UTC)),
    )


@router.get("/destinations", response_model=AdminPublishDestinationsResponse)
async def get_destinations() -> AdminPublishDestinationsResponse:
    async with get_session() as session:
        rows = await session.exec(
            select(PublishDestination).order_by(col(PublishDestination.created_at))
        )
        return AdminPublishDestinationsResponse(
            destinations=[AdminPublishDestination.from_row(row) for row in rows.all()]
        )


@router.post(
    "/destinations",
    response_model=AdminPublishDestination,
    status_code=status.HTTP_201_CREATED,
)
async def add_destination(body: PublishDestinationUpsert) -> AdminPublishDestination:
    try:
        config = config_to_store(body.config)
    except MissingSecretError as exc:
        raise _missing_secret(exc) from exc

    async with get_session() as session:
        row = PublishDestination(
            name=body.name,
            kind=body.config.kind,
            config=config,
            datasets=list(body.datasets),
            enabled=body.enabled,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return AdminPublishDestination.from_row(row)


@router.put("/destinations/{destination_id}", response_model=AdminPublishDestination)
async def update_destination(
    destination_id: uuid.UUID, body: PublishDestinationUpsert
) -> AdminPublishDestination:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        try:
            config = config_to_store(body.config, row.config)
        except MissingSecretError as exc:
            raise _missing_secret(exc) from exc

        row.name = body.name
        row.kind = body.config.kind
        row.config = config
        row.datasets = list(body.datasets)
        row.enabled = body.enabled
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return AdminPublishDestination.from_row(row)


@router.post(
    "/destinations/{destination_id}/check", status_code=status.HTTP_204_NO_CONTENT
)
async def check_destination_route(destination_id: uuid.UUID) -> None:
    """
    Write a small file to the destination and delete it, so a token that
    cannot write is found here rather than in the middle of the night.
    """
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        config = row.parsed_config()

    try:
        await asyncio.to_thread(check_destination, config)
    except DestinationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_destination(destination_id: uuid.UUID) -> None:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.delete(row)
        await session.commit()
