from fastapi import APIRouter

from backend.llms.data import get_llms_data
from backend.utils.countries import CountryPortalAnno, get_country_portal_ranking

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models(country_portal: CountryPortalAnno):
    models = get_llms_data(country_portal)
    cached = get_country_portal_ranking(country_portal)

    if not cached:
        # No dynamic rankings yet, serve static data unchanged
        return {
            "data_timestamp": models.data_timestamp,
            "models": list(models.all.values()),
        }

    models_list = []
    for model in models.all.values():
        model_dict = model.model_dump()
        # When dynamic rankings are active, replace static data entirely:
        # models with votes get dynamic data, others get null
        model_dict["data"] = (
            cached.rankings[model.id] if model.id in cached.rankings else None
        )
        model_dict["prefs"] = (
            cached.preferences[model.id] if model.id in cached.preferences else None
        )
        models_list.append(model_dict)

    return {
        "data_timestamp": cached.timestamp,
        "models": models_list,
    }
