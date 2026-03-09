import json
import logging
from functools import lru_cache

from backend.llms.models import LLMData
from utils.logger import configure_logger
from utils.utils import LLMS_GENERATED_DATA_FILE, read_json

logger = configure_logger(logging.getLogger("dataset.queries"))


@lru_cache
def get_llms_data():
    """
    Load the generated models JSON data.
    Used to enrich conversations with model metadata (params count, energy consumption).
    """
    try:
        llms_data = read_json(LLMS_GENERATED_DATA_FILE)
        return {
            k: LLMData.model_validate(v)
            for k, v in llms_data["models"].items()
            if v.get("status") in ("enabled", "archived")
        }
    except FileNotFoundError:
        logger.error(f"Models JSON file not found at: {LLMS_GENERATED_DATA_FILE}")
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from: {LLMS_GENERATED_DATA_FILE}")
