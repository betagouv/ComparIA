import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, select

from utils.database.models.publish import (
    AdminPublishDestination,
    AdminPublishDestinationsResponse,
    AdminPublishRun,
    AdminPublishStatus,
    MissingSecretError,
    PublishDestination,
    PublishDestinationUpsert,
    PublishFrequency,
    config_to_store,
)
from utils.database.models.utils import utc_now
from utils.database.session import get_session
from utils.dataset.runs import last_run, recent_runs
from utils.dataset.schedule import next_run_at

router = APIRouter(prefix="/publishing", tags=["publishing"])


def _request_publication(row: PublishDestination) -> None:
    """
    Ask the publish job for a run of this destination. A request already
    waiting keeps its date: what the panel shows is how long it has waited.
    """
    if row.publish_requested_at is None:
        row.publish_requested_at = utc_now()


def _missing_secret(exc: MissingSecretError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"'{exc.field}' is required for this kind of destination",
    )


def _frequency_activated(
    row: PublishDestination, previous_frequency: PublishFrequency | None = None
) -> bool:
    """
    Whether the destination's current state warrants a fresh publish request:
    enabled, a frequency other than off, and — when a previous frequency is
    given — a change from it. Creating a destination has no previous
    frequency to compare against.
    """
    if not row.enabled or row.publish_frequency == "off":
        return False
    return previous_frequency is None or row.publish_frequency != previous_frequency


def _to_admin_destination(row: PublishDestination) -> AdminPublishDestination:
    destination = AdminPublishDestination.from_row(row)
    destination.next_run_at = next_run_at(row.publish_frequency, datetime.now(UTC))
    return destination


@router.get("/status", response_model=AdminPublishStatus)
async def get_status() -> AdminPublishStatus:
    runs = await recent_runs()
    return AdminPublishStatus(
        runs=[AdminPublishRun.model_validate(run.model_dump()) for run in runs],
    )


@router.get("/destinations", response_model=AdminPublishDestinationsResponse)
async def get_destinations() -> AdminPublishDestinationsResponse:
    async with get_session() as session:
        rows = await session.exec(
            select(PublishDestination).order_by(col(PublishDestination.created_at))
        )
        destinations = [_to_admin_destination(row) for row in rows.all()]
        return AdminPublishDestinationsResponse(destinations=destinations)


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
            publish_frequency=body.publish_frequency,
        )
        if _frequency_activated(row):
            _request_publication(row)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _to_admin_destination(row)


@router.put("/destinations/{destination_id}", response_model=AdminPublishDestination)
async def update_destination(
    destination_id: uuid.UUID, body: PublishDestinationUpsert
) -> AdminPublishDestination:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        previous_frequency = row.publish_frequency
        try:
            config = config_to_store(body.config, row.config)
        except MissingSecretError as exc:
            raise _missing_secret(exc) from exc

        row.name = body.name
        row.kind = body.config.kind
        row.config = config
        row.datasets = list(body.datasets)
        row.enabled = body.enabled
        row.publish_frequency = body.publish_frequency
        if _frequency_activated(row, previous_frequency):
            _request_publication(row)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _to_admin_destination(row)


@router.post(
    "/destinations/{destination_id}/publish", status_code=status.HTTP_202_ACCEPTED
)
async def publish_destination_now(destination_id: uuid.UUID) -> None:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        if not row.enabled:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The destination is disabled",
            )
        run = await last_run()
        if run is not None and run.finished_at is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A publication is already running",
            )
        _request_publication(row)
        session.add(row)
        await session.commit()


@router.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_destination(destination_id: uuid.UUID) -> None:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.delete(row)
        await session.commit()
