import json5

from backend.config import (
    BIG_MODELS_BUCKET_LOWER_LIMIT,
    MODELS_DATA_PATH,
    SMALL_MODELS_BUCKET_UPPER_LIMIT,
)
from backend.models.utils import filter_enabled_models

# Load model definitions from generated configuration
# File contains metadata: params, pricing, reasoning capability, licenses, etc.
all_models_data = json5.loads(MODELS_DATA_PATH.read_text())

# Filter to only enabled models (removes disabled or deprecated models)
models = filter_enabled_models(all_models_data["models"])


# All models (for standard random selection)
random_pool = [id for id, _model in models.items()]

# Models with parameters <= 60B (for "small-models" selection mode)
small_models = [
    id
    for id, model in models.items()
    if model["params"] <= SMALL_MODELS_BUCKET_UPPER_LIMIT
]

# Models with parameters >= 100B (for "big-vs-small" selection mode)
big_models = [
    id
    for id, model in models.items()
    if model["params"] >= BIG_MODELS_BUCKET_LOWER_LIMIT
]

# Commercial models with higher API costs (e.g., Claude, GPT-4)
# These have stricter rate limits applied
pricey_models = [id for id, model in models.items() if model.get("pricey", False)]
