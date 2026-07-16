from fastapi import APIRouter

from utils.database.models.app_settings import AppSettingsPublic
from utils.database.settings import get_app_settings, to_app_settings_public

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
)


@router.get("/")
async def get_settings() -> AppSettingsPublic:
    return to_app_settings_public(await get_app_settings())
