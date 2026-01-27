from fastapi import APIRouter

from backend.llms.data import get_llms_data

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models():
    models = get_llms_data()
    # Convert dict to list of model objects for frontend compatibility
    return {
        "data_timestamp": models.data_timestamp,
        "models": list(models.all.values()),
    }
