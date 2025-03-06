import psycopg2
import json
import time
import logging
from typing import Optional
import vertexai
from vertexai.generative_models import GenerativeModel


class Config:
    PROJECT_ID = "languia-430909"  # Update with your GCP project ID
    LOCATION = "europe-west1"                 # Update with your preferred location
    MODEL_NAME = "gemini-2.0-flash-001"
    MAX_RETRIES = 3
    RETRY_DELAY = 1

    PROMPT_TEMPLATE = (
        "Task: Identify if text contains personal, sensitive, or private information.\n"
        "Rules:\n"
        "- Answer ONLY with single word 'true' or 'false'\n"
        "- true = contains personal info (names, emails, addresses) or sensitive info (medical, financial)\n"
        "- false = no personal or sensitive info\n\n"
        "Text: {text}\n"
        "Answer: "
    )


class PrivacyClassifier:
    def __init__(self):
        self.model = self._initialize_model()

    def _initialize_model(self):
        """Initialize Vertex AI and load the model"""
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            print(f"Model initialization failed: {str(e)}")
            return None

    def _get_classification(self, text: str) -> Optional[bool]:
        """Get classification from model with retries"""
        prompt = Config.PROMPT_TEMPLATE.format(text=text)

        for attempt in range(Config.MAX_RETRIES):
            try:
                start_time = time.time()
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.7,
                        "max_output_tokens": 1,
                    }
                )
                elapsed = time.time() - start_time

                content = response.text.lower().strip().rstrip('.')

                if content in ['true', 'false']:
                    result = content == 'true'
                    print(f"Text: '{text[:50]}...', Result: {result}, Time: {elapsed:.2f}s") #inline log
                    return result
                else:
                    print(f"Warning: Unexpected response: {response.text}") #inline log

            except Exception as e:
                print(f"Warning: Attempt {attempt + 1} failed: {str(e)}") #inline log
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        print (f"Error: max retries reached for text: '{text[:50]}...'") #inline log
        return None

    def analyze_text(self, text: str) -> Optional[bool]:
        return self._get_classification(text)


def process_conversations(db_params, classifier: PrivacyClassifier):
    """
    Processes conversations from the database, analyzes for PII, and updates the database.
    """
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()

        # Fetch conversations where pii_analyzed is false
        cursor.execute("SELECT id, conversation_a, conversation_b FROM conversations WHERE pii_analyzed = FALSE;")
        conversations = cursor.fetchall()

        for conversation_id, conversation_a, conversation_b in conversations:
            contains_pii = False
            question_content_a = ""
            question_content_b = ""

            # Extract question_content from conversation_a
            if conversation_a:
                for message in conversation_a:
                    if message.get("role") == "user":
                        question_content_a += message.get("content", "") + " "

            # Extract question_content from conversation_b
            if conversation_b:
                for message in conversation_b:
                    if message.get("role") == "user":
                        question_content_b += message.get("content", "") + " "

            # Analyze for PII
            if classifier.analyze_text(question_content_a) or classifier.analyze_text(question_content_b):
                contains_pii = True

            # Update the database
            cursor.execute(
                "UPDATE conversations SET pii_analyzed = TRUE, contains_pii = %s WHERE id = %s;",
                (contains_pii, conversation_id),
            )

        conn.commit()
        print("Conversations processed successfully.")

    except psycopg2.Error as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()
