import json
import argparse
from pathlib import Path
import logging
from typing import List, Set, Optional
from collections import defaultdict
from tqdm import tqdm
from pydantic import BaseModel
from enum import Enum
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from datasets import load_dataset
import time

# Define response schema matching your Pydantic model
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "contains_sensitive_info": {"type": "BOOLEAN"},
        "short_summary": {"type": "STRING"},
        "keywords": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        },
        "txt360_categories": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        },
        "languages": {
            "type": "ARRAY",
            "items": {"type": "STRING"}
        }
    }
}

class Config:
    PROJECT_ID = "languia-430909"  # Update with your GCP project ID
    LOCATION = "europe-west1"                 # Update with your preferred location
    MODEL_NAME = "gemini-2.0-flash"
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    BATCH_SIZE = 50
    SAVE_INTERVAL = 50
    DEFAULT_SAMPLE_SIZE = None

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
    natural_science_formal_science_technology = "Natural Science & Formal Science & Technology"
    personal_development_human_resources_career = "Personal Development & Human Resources & Career"
    politics_government = "Politics & Government"
    religion_spirituality = "Religion & Spirituality"
    shopping_commodity = "Shopping & Commodity"
    society_social_issues_human_rights = "Society & Social Issues & Human Rights"
    sports = "Sports"
    # needed!
    # history = "History"
    # philosophy = "Philosophy"
    other = "Other"

class AnalysisResult(BaseModel):
    # contains_sensitive_info: bool
    short_summary: str
    keywords: List[str]
    txt360_categories: List[TXT360Category]
    languages: List[str]

class Classifier:
    def __init__(self, output_dir: str = 'results-topic'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        self.model = self._initialize_model()
        self.processed_ids = set()
        self._load_processed_ids()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'classification.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _initialize_model(self):
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
            return None

    def _load_processed_ids(self):
        try:
            with open(self.output_dir / 'results.jsonl', 'r') as f:
                for line in f:
                    record = json.loads(line)
                    self.processed_ids.add(record["conversation_pair_id"])
                print("Loaded "+str(len(self.processed_ids))+ " already processed IDs.")
        except FileNotFoundError:
            pass

    def _process_conversation_pair(self, pair_id: str, records: List[dict]) -> Optional[dict]:
        try:
            record = max(records, key=lambda r: r.get("msg_rank", 0))
            conversation_a = json.dumps(record.get("conversation_a"))
            conversation_b = json.dumps(record.get("conversation_b"))

            analysis = self._analyze_content(conversation_a, conversation_b, pair_id)
            print(analysis)
            return analysis
        except Exception as e:
            self.logger.error(f"Error processing pair {pair_id}: {str(e)}")
            return None

    def _analyze_content(self, conv_a: str, conv_b: str, pair_id: str) -> Optional[dict]:
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = self.model.generate_content(
                    self._build_prompt(conv_a, conv_b),
                    generation_config=GenerationConfig(
                        temperature=0.7,
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA
                    )
                )
                result = AnalysisResult.parse_raw(response.text)
                return {
                    "conversation_pair_id": pair_id,
                    # "contains_sensitive_info": result.contains_sensitive_info,
                    "short_summary": result.short_summary,
                    "keywords": result.keywords,
                    "txt360_categories": [c.value for c in result.txt360_categories],
                    "languages": result.languages
                }
            except Exception as e:
                self.logger.warning(f"Attempt {attempt+1} failed: {str(e)}")
                time.sleep(Config.RETRY_DELAY)
        return None

    def _build_prompt(self, conv_a: str, conv_b: str) -> str:
        return f"""Analyze this conversation pair and return JSON in this structure:
{{
    "short_summary": string,
    "keywords": string[],
    "txt360_categories": TXT360Category[],
    "languages": string[]
}}

Categories: {[e.value for e in TXT360Category]}
Guidelines:
1. Extract 5-7 keywords
2. Assign relevant categories
3. Identify languages used ('fr', 'en', etc.)

Conversation A:
{conv_a}

Conversation B:
{conv_b}
"""

    def process_batch(self, batch: List[dict]) -> List[dict]:
        results = []
        grouped = defaultdict(list)
        
        for item in batch:
            grouped[item["conversation_pair_id"]].append(item)

        for pair_id, records in tqdm(grouped.items(), desc="Processing pairs"):
            if pair_id in self.processed_ids:
                print("Skipping already processed ID: "+pair_id)
                continue
            print("Processing ID: "+pair_id)
            result = self._process_conversation_pair(pair_id, records)
            if result:
                results.append(result)
                self._save_results([result])
                self.processed_ids.add(pair_id)

        return results

    def _save_results(self, results: List[dict]):
        try:
            with open(self.output_dir / 'results.jsonl', 'a') as f:
                for res in results:
                    f.write(json.dumps(res) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to save results: {str(e)}")

    def process_dataset(self, hf_token: str, num_samples: Optional[int] = None):
        try:
            ds = load_dataset("ministere-culture/comparia-questions", token=hf_token)
            total_available = len(ds['train'])
            print("Total lines to analyze: "+str(total_available))
            num_samples = num_samples or total_available

            self.logger.info(f"Processing {num_samples} out of {total_available} questions")

            all_results = []
            for i in range(0, num_samples, Config.BATCH_SIZE):
                batch_size = min(Config.BATCH_SIZE, num_samples - i)
                batch = ds['train'].select(range(i, i + batch_size))
                batch_results = self.process_batch(batch)
                all_results.extend(batch_results)
                
        except Exception as e:
            self.logger.error(f"Processing dataset failed: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='Conversation Analyzer')
    parser.add_argument('--token', type=str, required=True, help='Hugging Face token')
    parser.add_argument('--samples', type=int, default=Config.DEFAULT_SAMPLE_SIZE, help='Number of samples to process')
    parser.add_argument('--output', type=str, default='results-output', help='Output directory')
    
    args = parser.parse_args()
    
    analyzer = Classifier(output_dir=args.output)
    analyzer.process_dataset(hf_token=args.token, num_samples=args.samples)

if __name__ == "__main__":
    main()
