import uuid

from fastapi import APIRouter, HTTPException, status
from sqlmodel import col, select

from utils.database.models.publish import (
    AdminPublishDestination,
    AdminPublishDestinationsResponse,
    MissingSecretError,
    PublishDestination,
    PublishDestinationUpsert,
    config_to_store,
)
from utils.database.session import get_session

router = APIRouter(prefix="/publishing", tags=["publishing"])


def _missing_secret(exc: MissingSecretError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"'{exc.field}' is required for this kind of destination",
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


@router.delete("/destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_destination(destination_id: uuid.UUID) -> None:
    async with get_session() as session:
        row = await session.get(PublishDestination, destination_id)
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        await session.delete(row)
        await session.commit()
