from fastapi import APIRouter

from backend.llms.data import get_llms_data
from backend.utils.countries import get_ranking

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/")
async def get_available_models():
    models = await get_llms_data()
    data = get_ranking()

    if not data:
        # No dynamic rankings yet, serve llm data without ranking
        return {
            "data_timestamp": None,
            "models": list(models.all.values()),
        }

    models_list = []
    for model in models.all.values():
        model_dict = model.model_dump()
        # Populate model definitions with ranking and prefs data if available
        model_dict["data"] = (
            data.rankings[model.id] if model.id in data.rankings else None
        )
        model_dict["prefs"] = (
            data.preferences[model.id] if model.id in data.preferences else None
        )
        models_list.append(model_dict)

    return {
        "data_timestamp": data.timestamp,
        "models": models_list,
        # Global style-control coefficients (one per presentation feature), for
        # the transparency panel on the ranking page's methodology tab.
        "style_coefficients": data.style_coefficients,
    }
