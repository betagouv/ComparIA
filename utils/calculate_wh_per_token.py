import pandas as pd
import logging
import sys
import os
import json
import litellm
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_JSON_PATH = os.path.join(SCRIPT_DIR, 'models', 'generated-models.json')

def get_distinct_model_ids(engine):
    """Get distinct model IDs from the conversations table."""
    query = "SELECT DISTINCT model_a_name as model_id FROM conversations UNION SELECT DISTINCT model_b_name as model_id FROM conversations"
    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
            # Filter out None values if any
            return df['model_id'].dropna().unique().tolist()
    except Exception as e:
        logger.error(f"Failed to fetch distinct model IDs: {e}")
        return []

def load_models_data():
    """Load the generated models JSON data."""
    try:
        with open(MODELS_JSON_PATH, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Models JSON file not found at: {MODELS_JSON_PATH}")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from: {MODELS_JSON_PATH}")
        return None

def main():
    """Main function to calculate and display wh_per_million_token."""
    DATABASE_URI = os.getenv("DATABASE_URI")
    if not DATABASE_URI:
        logger.error("Cannot connect to the database: no $DATABASE_URI configuration provided.")
        sys.exit(1)

    try:
        engine = create_engine(DATABASE_URI)
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        sys.exit(1)

    model_ids_from_db = get_distinct_model_ids(engine)
    if not model_ids_from_db:
        logger.error("No model IDs found in the database.")
        sys.exit(1)

    models_data = load_models_data()
    if not models_data:
        sys.exit(1)

    missing_models = []
    model_encoder_data = {}

    # Pre-check for missing models in generated-models.json
    for model_id in model_ids_from_db:
        if model_id not in models_data:
            missing_models.append(f"'{model_id}' not found in generated-models.json")

    if missing_models:
        logger.warning("Pre-check found missing models in generated-models.json:")
        for model in missing_models:
            logger.warning(f"- {model}")

    # Get encoder info for each model
    for model_id in model_ids_from_db:
        if model_id in models_data:
            try:
                # Get the tokenizer for the model
                tokenizer = litellm.get_tokenizer(model_id)
                if tokenizer:
                    model_encoder_data[model_id] = tokenizer.name
                else:
                    model_encoder_data[model_id] = "Tokenizer not found"
            except Exception as e:
                model_encoder_data[model_id] = f"Could not get tokenizer: {e}"


    logger.info("\nLiteLLM Encoder Information:")
    for model_id, encoder_name in sorted(model_encoder_data.items()):
        print(f"{model_id}: {encoder_name}")

if __name__ == "__main__":
    main()
