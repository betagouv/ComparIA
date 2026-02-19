import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import List, Optional, Tuple

import psycopg2
import vertexai
from vertexai.generative_models import GenerativeModel

# Used in kubernetes (cron job)
# FIXME: change model for cheeper model? (still gemini)


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
            Analyze the following two conversations and determine if they contain personal info (names, emails, addresses) or sensitive info (medical, financial), categorize them, extract keywords (5 to 7, careful not to use PIIs in it), provide a short summary (don't use PIIs in summary), and identify the languages used (2-letter codes).
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


def process_conversation(conversation, analyzer, db_params):
    conn = None
    conversation_pair_id = conversation[0]  # Extract ID early
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        (
            _,  # conversation_pair_id already extracted
            conversation_a,
            conversation_b,
            existing_summary,
            existing_keywords,
            existing_languages,
            existing_contains_pii,
            existing_pii_analyzed,
            postprocess_failed,  # Retrieve the new field
        ) = conversation

        print(f"Processing conversation pair ID: {conversation_pair_id}")
        if postprocess_failed:
            print(
                f"Conversation {conversation_pair_id} marked as postprocess failed, skipping."
            )
            return None

        if existing_summary or existing_keywords or existing_languages:
            print(f"Conversation {conversation_pair_id} already has data:")
            print(f"  Short Summary: {existing_summary}")
            print(f"  Keywords: {existing_keywords}")
            print(f"  Languages: {existing_languages}")
            print(f"  Contains PII: {existing_contains_pii}")
            print(f"  PII Analyzed: {existing_pii_analyzed}")
            return None  # Indicate no analysis was performed

        for attempt in range(Config.MAX_RETRIES):
            print(
                f"Attempt {attempt + 1}/{Config.MAX_RETRIES} for conversation pair ID: {conversation_pair_id}"
            )
            contains_pii, categories, keywords, short_summary, languages = (
                analyzer.analyze_conversations(
                    conversation_a, conversation_b, conversation_pair_id
                )
            )
            # If llm call worked, insert metadata in db
            if contains_pii is not None:
                print(f"Data to be inserted for {conversation_pair_id}:")
                print(f"  Short Summary: {short_summary}")
                print(f"  Keywords: {keywords}")
                print(f"  Languages: {languages}")
                print(f"  categories: {categories}")
                print(f"  Contains PII: {contains_pii}")
                cursor.execute(
                    "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s, short_summary = %s, keywords = %s, categories = %s, languages = %s, postprocess_failed = FALSE WHERE conversation_pair_id = %s;",
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
                return None  # Return None if successful
            else:
                print(
                    f"Analysis failed for conversation pair ID: {conversation_pair_id} on attempt {attempt + 1}."
                )
                if attempt < Config.MAX_RETRIES - 1:
                    print(f"Retrying in {Config.RETRY_DELAY} second(s)...")
                    time.sleep(Config.RETRY_DELAY)

        # If all retries failed
        print(
            f"Analysis failed after {Config.MAX_RETRIES} retries for conversation pair ID: {conversation_pair_id}"
        )
        with open("topics-pii-error.log", "a") as f:
            f.write(f"{conversation_pair_id}\n")
        cursor.execute(
            "UPDATE conversations SET postprocess_failed = TRUE WHERE conversation_pair_id = %s;",
            (conversation_pair_id,),
        )
        conn.commit()
        return conversation_pair_id  # return the id of the failed conversation
    except psycopg2.Error as e:
        print(
            f"Database Error in process_conversation for ID {conversation_pair_id}: {e}"
        )
        return conversation_pair_id
    finally:
        if conn:
            cursor.close()
            conn.close()


def process_conversations(db_params, analyzer: Config):
    conn = None
    failed_calls = []
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE short_summary IS NULL AND postprocess_failed = FALSE;"
        )
        no_summary_count = cursor.fetchone()[0]
        print(
            f"{no_summary_count} conversations with no short summary and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE keywords IS NULL AND postprocess_failed = FALSE;"
        )
        no_keywords_count = cursor.fetchone()[0]
        print(
            f"{no_keywords_count} conversations with no keywords and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE short_summary IS NOT NULL AND postprocess_failed = FALSE;"
        )
        summary_count = cursor.fetchone()[0]
        print(
            f"{summary_count} conversations with a short summary and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE keywords IS NOT NULL AND postprocess_failed = FALSE;"
        )
        keywords_count = cursor.fetchone()[0]
        print(f"{keywords_count} conversations with keywords and not marked as failed.")

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE contains_pii = FALSE AND postprocess_failed = FALSE;"
        )
        contains_pii_false_count = cursor.fetchone()[0]
        print(
            f"{contains_pii_false_count} conversations with contains_pii = FALSE and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE contains_pii = TRUE AND postprocess_failed = FALSE;"
        )
        contains_pii_true_count = cursor.fetchone()[0]
        print(
            f"{contains_pii_true_count} conversations with contains_pii = TRUE and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE contains_pii IS NULL AND postprocess_failed = FALSE;"
        )
        contains_pii_null_count = cursor.fetchone()[0]
        print(
            f"{contains_pii_null_count} conversations with contains_pii = NULL and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE pii_analyzed = FALSE AND postprocess_failed = FALSE;"
        )
        pii_analyzed_false_count = cursor.fetchone()[0]
        print(
            f"{pii_analyzed_false_count} conversations with pii_analyzed = FALSE and not marked as failed."
        )

        cursor.execute(
            "SELECT count(*) FROM conversations WHERE pii_analyzed = TRUE AND postprocess_failed = FALSE;"
        )
        pii_analyzed_true_count = cursor.fetchone()[0]
        print(
            f"{pii_analyzed_true_count} conversations with pii_analyzed = TRUE and not marked as failed."
        )

        # Include the postprocess_failed field in the select statement and filter
        cursor.execute(
            "SELECT conversation_pair_id, conversation_a, conversation_b, short_summary, keywords, languages, contains_pii, pii_analyzed, postprocess_failed FROM conversations WHERE (pii_analyzed = FALSE OR short_summary IS NULL) AND postprocess_failed = FALSE;"
        )

        conversations_to_process = cursor.fetchall()
        cursor.close()

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(process_conversation, conversation, analyzer, db_params)
                for conversation in conversations_to_process
            ]
            for future in futures:
                result = future.result()
                if result is not None:
                    failed_calls.append(result)

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


db_params = os.getenv("COMPARIA_DB_URI")
analyzer = Config()
process_conversations(db_params, analyzer)
