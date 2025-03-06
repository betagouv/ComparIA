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


# class TXT360Category(str, Enum):
#     arts = "Arts"
#     business_economics_finance = "Business & Economics & Finance"
#     culture_cultural_geography = "Culture & Cultural geography"
#     daily_life_home_lifestyle = "Daily Life & Home & Lifestyle"
#     education = "Education"
#     entertainment_travel_hobby = "Entertainment & Travel & Hobby"
#     environment = "Environment"
#     food_drink_cooking = "Food & Drink & Cooking"
#     health_wellness_medicine = "Health & Wellness & Medicine"
#     law_justice = "Law & Justice"
#     natural_science_formal_science_technology = (
#         "Natural Science & Formal Science & Technology"
#     )
#     personal_development_human_resources_career = (
#         "Personal Development & Human Resources & Career"
#     )
#     politics_government = "Politics & Government"
#     religion_spirituality = "Religion & Spirituality"
#     shopping_commodity = "Shopping & Commodity"
#     society_social_issues_human_rights = "Society & Social Issues & Human Rights"
#     sports = "Sports"
#     # needed!
#     # history = "History"
#     # philosophy = "Philosophy"
#     other = "Other"

    PROMPT_TEMPLATE = (
        "Task: Analyze conversations for PII, categories, keywords, short summary, and languages.\n"
        "Rules:\n"
        "- PII: Identify if text contains personal or sensitive information. Answer with 'true' or 'false' for each user message.\n"
        "- Categories: Provide a list of relevant categories based on the conversation content.\n"
        
        "- Keywords: Extract 5 to 7 keywords from the conversation.\n"
        "- Short Summary: Provide a concise summary of the conversation.\n"
        "- Languages: Identify the languages used in the conversation (2-letters code).\n"
        "- Output format: JSON with fields 'contains_pii', 'categories', 'keywords', 'short_summary', 'languages'.\n"
        "- 'categories', 'keywords', and 'languages' should be lists of strings.\n"
        "- 'short_summary' should be a string.\n\n"
        "Conversation A: {conversation_a}\n"
        "Conversation B: {conversation_b}\n"
        "Answer: "
    )

class ConversationAnalyzer:
    def __init__(self):
        self.model = self._initialize_model()

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            print(f"Model initialization failed: {str(e)}")
            return None

    def _analyze_conversation(self, conversation_a: List[dict], conversation_b: List[dict]) -> Optional[dict]:
        conversation_a_str = json.dumps(conversation_a)
        conversation_b_str = json.dumps(conversation_b)
        prompt = Config.PROMPT_TEMPLATE.format(conversation_a=conversation_a_str, conversation_b=conversation_b_str)

        for attempt in range(Config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.model.generate_content(
                    prompt,
                    generation_config={"temperature": 0.7, "max_output_tokens": 1024},
                )
                elapsed = time.time() - start_time
                content = response.text.strip()

                try:
                    analysis_result = json.loads(content)
                    print(f"Analysis successful, Time: {elapsed:.2f}s")
                    return analysis_result
                except json.JSONDecodeError:
                    print(f"Warning: Unexpected response format: {content}")

            except Exception as e:
                print(f"Warning: Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)

        print(f"Error: Max retries reached for conversation: {conversation_a_str[:100]}...")
        return None

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

def get_conv_b_index(conversation_a, conversation_b, a_index):
    if not conversation_a or not conversation_b:
        return None
    offset_a = 1 if conversation_a and conversation_a[0].get("role") == "system" else 0
    offset_b = 1 if conversation_b and conversation_b[0].get("role") == "system" else 0
    return a_index - offset_a + offset_b

def process_conversations(db_params, analyzer: ConversationAnalyzer):
    try:
        conn = psycopg2.connect(db_params)
        cursor = conn.cursor()

        cursor.execute("SELECT conversation_pair_id, conversation_a, conversation_b FROM conversations WHERE pii_analyzed = FALSE;")
        conversations = cursor.fetchall()

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