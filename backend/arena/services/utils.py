import uuid
from typing import TYPE_CHECKING, TypeVar

from fastapi import HTTPException, status

from utils.database.models import Comparison, Turn

if TYPE_CHECKING:
    from sqlmodel.ext.asyncio.session import AsyncSession

T = TypeVar("T", bound=Comparison | Turn)


async def get_item(item_class: type[T], id: uuid.UUID, session: "AsyncSession") -> T:
    db_item = await session.get(item_class, id)

    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{item_class.__name__} not found",
        )

    return db_item
