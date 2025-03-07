import psycopg2
import json
import time
import vertexai
from vertexai.generative_models import GenerativeModel
from typing import Optional, List, Tuple
import os
from enum import Enum

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

    def _analyze_conversation(self, conversation_a: List[dict], conversation_b: List[dict]) -> Optional[dict]:
        print("Analyzing conversation...")
        try:
            vertexai.init(project=self.PROJECT_ID, location=self.LOCATION)
            model = GenerativeModel(self.MODEL_NAME)

            prompt = f"""
            Analyze the following two conversations and determine if they contain PII, categorize them, extract keywords (5 to 7), provide a short summary, and identify the languages used (2-letter codes).
            Conversation A: {conversation_a}
            Conversation B: {conversation_b}

            Return the response in the following JSON schema:
            {json.dumps(self.response_schema, indent=2)}
            """

            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            print("Gemini API response received.")
            try:
                analysis_result = json.loads(response.text)[0]
                print("Analysis result parsed successfully.")
                return analysis_result
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON response: {e}, response text: {response.text}")
                return None

        except Exception as e:
            print(f"Error during analysis: {e}")
            return None

    def analyze_conversations(self, conversation_a: List[dict], conversation_b: List[dict], conversation_id: int) -> Tuple[Optional[List[dict]], Optional[List[dict]], Optional[List[str]], Optional[str], Optional[List[str]]]:
        print(f"Analyzing conversation pair ID: {conversation_id}")
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


def process_conversations(db_params, analyzer: Config):
    conn = None
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        cursor.execute("SELECT count(*) FROM conversations WHERE pii_analyzed = FALSE OR short_summary IS NULL;")
        count = cursor.fetchone()[0]
        print(f"{count} conversations to enrich...")
        
        cursor.execute("SELECT conversation_pair_id, conversation_a, conversation_b FROM conversations WHERE pii_analyzed = FALSE OR short_summary IS NULL;")
        failed_calls = []
        while True:
            conversation = cursor.fetchone()
            if conversation is None:
                break
            conversation_id, conversation_a, conversation_b = conversation

            print(f"Processing conversation pair ID: {conversation_id}")
            contains_pii, categories, keywords, short_summary, languages = analyzer.analyze_conversations(conversation_a, conversation_b, conversation_id)
            if contains_pii is None:
                print(f"Analysis failed for conversation pair ID: {conversation_id}")
                with open("topics-pii-error.log", "a") as f:
                    f.write(f"{conversation_id}\n")
                continue


            cursor.execute(
                "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s, short_summary = %s, keywords = %s, categories = %s, languages = %s WHERE conversation_pair_id = %s;",
                (contains_pii, short_summary, json.dumps(keywords), json.dumps(categories), json.dumps(languages), conversation_id),
            )
            conn.commit()
            print(f"Conversation pair ID: {conversation_id} enriched successfully.")

        if failed_calls:
            print(f"Failed calls for conversation_pair_ids: {failed_calls}")

            with open("topics-pii-error.log", "a") as f:
                f.write(f"{failed_calls}\n")

    except psycopg2.Error as e:
        print(f"Database Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()

db_params = os.getenv("DATABASE_URI")
analyzer = Config()
process_conversations(db_params, analyzer)