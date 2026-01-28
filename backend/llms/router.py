from fastapi import APIRouter

from backend.llms.data import get_llms_data
from backend.utils.countries import CountryPortalAnno

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models(country_portal: CountryPortalAnno):
    models = get_llms_data(country_portal)
    # Convert dict to list of model objects for frontend compatibility
    return {
        "data_timestamp": models.data_timestamp,
        "models": list(models.all.values()),
    }
