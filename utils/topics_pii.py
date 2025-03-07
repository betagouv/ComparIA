import psycopg2
import json
import time
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Optional, List, Tuple
import os

class Config:
    PROJECT_ID = "languia-430909"
    LOCATION = "europe-west1"
    MODEL_NAME = "gemini-2.0-flash-001"
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    class TXT360Category(str, Enum):
        arts = "Arts"
        business_economics_finance = "Business & Economics & Finance"
        culture_cultural_geography = "Culture & Cultural geography"
        daily_life_home_lifestyle = "Daily Life & Home & Lifestyle"
        education = "Education"
        entertainment_travel_hobby = "Entertainment & Travel & Hobby"
        environment = "Environment"
        food_drink_cooking = "Food & Drink & Cooking"
        health_wellness_medicine = "Health & Wellness & Medicine"
        law_justice = "Law & Justice"
        natural_science_formal_science_technology = (
            "Natural Science & Formal Science & Technology"
        )
        personal_development_human_resources_career = (
            "Personal Development & Human Resources & Career"
        )
        politics_government = "Politics & Government"
        religion_spirituality = "Religion & Spirituality"
        shopping_commodity = "Shopping & Commodity"
        society_social_issues_human_rights = "Society & Social Issues & Human Rights"
        sports = "Sports"
        other = "Other"

    response_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "contains_pii": {"type": "BOOLEAN"},
                "categories": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING",
                        "enum": [category.value for category in TXT360Category],
                    },
                },
                "keywords": {"type": "ARRAY", "items": {"type": "STRING"}},
                "short_summary": {"type": "STRING"},
                "languages": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": ["contains_pii", "categories", "keywords", "short_summary", "languages"],
        },
    }

    def analyze_conversations(self, conversation_a: List[dict], conversation_b: List[dict], conversation_id: int) -> Tuple[Optional[List[dict]], Optional[List[dict]], Optional[List[str]], Optional[str], Optional[List[str]]]:
        analysis_result = self._analyze_conversation(conversation_a, conversation_b)
        if analysis_result:
            contains_pii = analysis_result.get('contains_pii')
            categories = analysis_result.get('categories')
            keywords = analysis_result.get('keywords')
            short_summary = analysis_result.get('short_summary')
            languages = analysis_result.get('languages')

            return contains_pii, categories, keywords, short_summary, languages
        else:
            return None, None, None, None, None

def process_conversations(db_params, analyzer: ConversationAnalyzer):
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        cursor.execute("SELECT conversation_pair_id, conversation_a, conversation_b FROM conversations WHERE pii_analyzed = FALSE OR short_summary = NULL;")
        conversations = cursor.fetchall()
        print(f"{len(conversations)} to enrich...")
        failed_calls = []

        for conversation_id, conversation_a, conversation_b in conversations:
            contains_pii, categories, keywords, short_summary, languages = analyzer.analyze_conversations(conversation_a, conversation_b, conversation_id)
            if contains_pii is None:
                failed_calls.append(conversation_id)
                continue

            contains_pii = any(result['contains_pii'] for result in contains_pii)

            cursor.execute(
                "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s, short_summary = %s, keywords = %s, categories = %s, languages = %s WHERE conversation_pair_id = %s;",
                (contains_pii, short_summary, json.dumps(keywords), json.dumps(categories), json.dumps(languages), conversation_id),
            )
            conn.commit()

        if failed_calls:
            print(f"Failed calls for conversation_pair_ids: {failed_calls}")

            with open("topics-pii-error.log", "a") as f:
                f.write(f"{failed_calls}\n")

    except psycopg2.Error as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

db_params = os.getenv("DATABASE_URI")
analyzer = ConversationAnalyzer()
process_conversations(db_params, analyzer)