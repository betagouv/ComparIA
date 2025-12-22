from fastapi import APIRouter

from backend.language_models.data import get_models

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models():
    models = get_models()
    return {
        "data_timestamp": models.data_timestamp,
        "models": models.all,
    }
