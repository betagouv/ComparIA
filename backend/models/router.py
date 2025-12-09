from fastapi import APIRouter

from backend.models.data import all_models_data

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models():
    return {
        "models": [
            model
            for model in all_models_data["models"].values()
            if model["status"] in ("enabled", "archived")
        ],
        "data_timestamp": all_models_data["timestamp"],
    }
