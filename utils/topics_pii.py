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
    # MODEL_NAME = "gemini-2.0-flash-lite"
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
            "required": [
                "contains_pii",
                "categories",
                "keywords",
                "short_summary",
                "languages",
            ],
        },
    }

    def _analyze_conversation(
        self, conversation_a: List[dict], conversation_b: List[dict]
    ) -> Optional[dict]:
        print("Analyzing conversation...")
        try:
            vertexai.init(project=self.PROJECT_ID, location=self.LOCATION)
            model = GenerativeModel(self.MODEL_NAME)

            prompt = f"""
            Analyze the following two conversations and determine if they contain personal info (names, emails, addresses) or sensitive info (medical, financial), categorize them, extract keywords (5 to 7), provide a short summary, and identify the languages used (2-letter codes).
            Conversation A: {conversation_a}
            Conversation B: {conversation_b}

            Return the response in the following JSON schema:
            {json.dumps(self.response_schema, indent=2)}
            """

            response = model.generate_content(
                prompt, generation_config={"response_mime_type": "application/json"}
            )
            print("Gemini API response received.")
            try:
                analysis_result = json.loads(response.text)[0]
                print("Analysis result parsed successfully.")
                return analysis_result
            except json.JSONDecodeError as e:
                print(
                    f"Error decoding JSON response: {e}, response text: {response.text}"
                )
                return None

        except Exception as e:
            print(f"Error during analysis: {e}")
            return None

    def analyze_conversations(
        self,
        conversation_a: List[dict],
        conversation_b: List[dict],
        conversation_pair_id: int,
    ) -> Tuple[
        Optional[List[dict]],
        Optional[List[dict]],
        Optional[List[str]],
        Optional[str],
        Optional[List[str]],
    ]:
        print(f"Analyzing conversation pair ID: {conversation_pair_id}")
        analysis_result = self._analyze_conversation(conversation_a, conversation_b)
        if analysis_result:
            contains_pii = analysis_result.get("contains_pii")
            categories = analysis_result.get("categories")
            keywords = analysis_result.get("keywords")
            short_summary = analysis_result.get("short_summary")
            languages = analysis_result.get("languages")

            return contains_pii, categories, keywords, short_summary, languages
        else:
            return None, None, None, None, None


def process_conversations(db_params, analyzer: Config):
    conn = None
    failed_calls = []
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE short_summary IS NULL;"
        )
        no_summary_count = cursor.fetchone()[0]
        print(f"{no_summary_count} conversations with no short summary.")

        cursor.execute("SELECT count(*) FROM conversations WHERE keywords IS NULL;")
        no_keywords_count = cursor.fetchone()[0]
        print(f"{no_keywords_count} conversations with no keywords.")

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE short_summary IS NOT NULL;"
        )
        summary_count = cursor.fetchone()[0]
        print(f"{summary_count} conversations with a short summary.")

        cursor.execute("SELECT count(*) FROM conversations WHERE keywords IS NOT NULL;")
        keywords_count = cursor.fetchone()[0]
        print(f"{keywords_count} conversations with keywords.")

        cursor.execute("SELECT count(*) FROM conversations WHERE contains_pii = FALSE;")
        contains_pii_false_count = cursor.fetchone()[0]
        print(f"{contains_pii_false_count} conversations with contains_pii = FALSE.")

        cursor.execute("SELECT count(*) FROM conversations WHERE contains_pii = TRUE;")
        contains_pii_true_count = cursor.fetchone()[0]
        print(f"{contains_pii_true_count} conversations with contains_pii = TRUE.")

        cursor.execute("SELECT count(*) FROM conversations WHERE contains_pii IS NULL;")
        contains_pii_null_count = cursor.fetchone()[0]
        print(f"{contains_pii_null_count} conversations with contains_pii = NULL.")

        cursor.execute("SELECT count(*) FROM conversations WHERE pii_analyzed = FALSE;")
        pii_analyzed_false_count = cursor.fetchone()[0]
        print(f"{pii_analyzed_false_count} conversations with pii_analyzed = FALSE.")

        cursor.execute("SELECT count(*) FROM conversations WHERE pii_analyzed = TRUE;")
        pii_analyzed_true_count = cursor.fetchone()[0]
        print(f"{pii_analyzed_true_count} conversations with pii_analyzed = TRUE.")

        cursor.execute(
            "SELECT conversation_pair_id, conversation_a, conversation_b, short_summary, keywords, languages, contains_pii, pii_analyzed FROM conversations WHERE pii_analyzed = FALSE OR short_summary IS NULL;"
        )

        conversations_to_process = cursor.fetchall()
        for conversation in conversations_to_process:
            (    conversation_pair_id,
                conversation_a,
                conversation_b,
                existing_summary,
                existing_keywords,
                existing_languages,
                existing_contains_pii,
                existing_pii_analyzed,
            ) = conversation

            print(f"Processing conversation pair ID: {conversation_pair_id}")
            if (
                existing_summary
                or existing_keywords
                or existing_languages
                or existing_contains_pii is not None
                or existing_pii_analyzed
            ):
                print(f"Conversation {conversation_pair_id} already has data:")
                print(f"  Short Summary: {existing_summary}")
                print(f"  Keywords: {existing_keywords}")
                print(f"  Languages: {existing_languages}")
                print(f"  Contains PII: {existing_contains_pii}")
                print(f"  PII Analyzed: {existing_pii_analyzed}")

            contains_pii, categories, keywords, short_summary, languages = (
                analyzer.analyze_conversations(
                    conversation_a, conversation_b, conversation_pair_id
                )
            )
            if contains_pii is None:
                print(
                    f"Analysis failed for conversation pair ID: {conversation_pair_id}"
                )
                with open("topics-pii-error.log", "a") as f:
                    f.write(f"{conversation_pair_id}\n")
                continue

            
            print(f"Data to be inserted for {conversation_pair_id}:")
            print(f"  Short Summary: {short_summary}")
            print(f"  Keywords: {keywords}")
            print(f"  Languages: {languages}")
            print(f"  categories: {categories}")
            print(f"  Contains PII: {contains_pii}")
            cursor.execute(
                "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s, short_summary = %s, keywords = %s, categories = %s, languages = %s WHERE conversation_pair_id = %s;",
                (
                    contains_pii,
                    short_summary,
                    json.dumps(keywords),
                    json.dumps(categories),
                    json.dumps(languages),
                    conversation_pair_id,
                ),
            )
            conn.commit()
            print(
                f"Conversation pair ID: {conversation_pair_id} enriched successfully."
            )

        if failed_calls:
            print(f"Failed calls for conversation_pair_ids: {failed_calls}")

            with open("topics-pii-error.log", "a") as f:
                f.write(f"{failed_calls}\n")

    except psycopg2.Error as e:
        print(f"Database Error: {e}")
    finally:

        if failed_calls:
            print(f"Failed calls for conversation_pair_ids: {failed_calls}")

            with open("topics-pii-error.log", "a") as f:
                f.write(f"{failed_calls}\n")
        if conn:
            cursor.close()
            conn.close()


db_params = os.getenv("DATABASE_URI")
analyzer = Config()
process_conversations(db_params, analyzer)
