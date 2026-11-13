from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from backend.admin.selection_modes.models import (
    SelectionModeOrder,
    SelectionModePreview,
    SelectionModeTemplate,
)
from backend.admin.selection_modes.services import (
    CannotRemoveLastModeError,
    DefaultModeChangedError,
    MissingDefaultLabelError,
    ModeKeyImmutableError,
    ModeKeyTakenError,
    ModeNotFoundError,
    create_mode,
    delete_mode,
    list_modes,
    preview_mode,
    reorder_modes,
    update_mode,
)
from backend.admin.selection_modes.templates import TEMPLATES
from utils.database.models import (
    SelectionModeAdmin,
    SelectionModeRules,
    SelectionModeUpsert,
)
from utils.utils import FormJsonSchema

router = APIRouter(prefix="/selection-modes", tags=["selection-modes"])


@contextmanager
def _as_http() -> Iterator[None]:
    try:
        yield
    except ModeNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="mode_not_found")
    except ModeKeyTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="mode_key_taken")
    except ModeKeyImmutableError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="mode_key_immutable")
    except CannotRemoveLastModeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="last_enabled_mode")
    except DefaultModeChangedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="default_mode_changed")
    except MissingDefaultLabelError:
        # Shaped like a validation error, so the form shows it under the field.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {
                    "loc": ["body", "label"],
                    "msg": "label_missing_default_locale",
                    "type": "value_error",
                }
            ],
        )


@router.get("")
async def get_modes() -> list[SelectionModeAdmin]:
    return await list_modes()


@router.get("/schemas")
async def get_schemas():
    return {
        "selection_mode": SelectionModeUpsert.model_json_schema(
            schema_generator=FormJsonSchema
        )
    }


@router.get("/templates")
async def get_templates() -> list[SelectionModeTemplate]:
    return TEMPLATES


@router.post("/preview")
async def preview(body: SelectionModeRules) -> SelectionModePreview:
    # Only the rules: a form still being filled in has no key or label yet,
    # and the rest of an upsert body is ignored.
    return await preview_mode(body)


@router.post("")
async def create(body: SelectionModeUpsert) -> SelectionModeAdmin:
    with _as_http():
        return await create_mode(body)


@router.post("/reorder")
async def reorder(body: SelectionModeOrder) -> list[SelectionModeAdmin]:
    with _as_http():
        await reorder_modes(body.ids)
    return await list_modes()


@router.put("/{mode_id}")
async def update(mode_id: UUID, body: SelectionModeUpsert) -> SelectionModeAdmin:
    with _as_http():
        return await update_mode(mode_id, body)


@router.delete("/{mode_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(mode_id: UUID) -> None:
    with _as_http():
        await delete_mode(mode_id)
