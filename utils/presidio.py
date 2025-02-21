import json
import requests
from datasets import load_dataset
import argparse
from pathlib import Path
import time
from datetime import datetime
from tqdm import tqdm
import pandas as pd
from typing import Dict, List, Optional
import logging as logger


class Config:
    # API endpoints
    # ANALYZE_URL = "http://localhost:5002/analyze"
    # ANONYMIZE_URL = "http://localhost:5001/anonymize"
    # Presidio settings
    LANGUAGE = "fr"
    # Dataset settings
    BATCH_SIZE = 50
    DEFAULT_SAMPLE_SIZE = 500
    SAVE_INTERVAL = 50
    MAX_RETRIES = 3
    RETRY_DELAY = 1


class PrivacyStats:
    def __init__(self):
        self.total_processed = 0
        self.pii_detected = 0
        self.non_pii = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.response_times = []
        self.last_save_point = 0

    def add_result(self, pii_present: bool, time_taken: float):
        self.total_processed += 1
        if pii_present:
            self.pii_detected += 1
        else:
            self.non_pii += 1
        self.response_times.append(time_taken)

    def add_error(self):
        self.errors += 1
        self.total_processed += 1

    def should_save(self) -> bool:
        return (self.total_processed - self.last_save_point) >= Config.SAVE_INTERVAL

    def update_save_point(self):
        self.last_save_point = self.total_processed

    def get_summary(self) -> Dict:
        end_time = datetime.now()
        return {
            "total_processed": self.total_processed,
            "pii_detected": self.pii_detected,
            "non_pii": self.non_pii,
            "error_count": self.errors,
            "avg_response_time": (
                (sum(self.response_times) / len(self.response_times))
                if self.response_times
                else 0
            ),
            "total_time": str(end_time - self.start_time),
            "timestamp": end_time.isoformat(),
        }


class PrivacyClassifier:
    def __init__(self, output_dir: str = "results"):
        self.stats = PrivacyStats()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _call_api(self, url: str, payload: dict) -> Optional[dict]:
        for attempt in range(Config.MAX_RETRIES):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers={"Content-type": "application/json"},
                    timeout=10,
                )
                response.raise_for_status()
                print(response.json())
                return response.json()
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        return None


from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NlpEngineProvider

# Create configuration containing engine name and models
configuration = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "fr", "model_name": "fr_core_news_sm"}],
}

# Create NLP engine based on configuration
provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine_with_french = provider.create_engine()

from presidio_analyzer import (
    AnalyzerEngine,
    BatchAnalyzerEngine,
    RecognizerResult,
    DictAnalyzerResult,
)
from presidio_anonymizer import AnonymizerEngine, BatchAnonymizerEngine
from presidio_anonymizer.entities import EngineResult

# Dataset settings
BATCH_SIZE = 50  # Size of batches for processing
DEFAULT_SAMPLE_SIZE = 5  # None means process all entries
SAVE_INTERVAL = 50  # Save results every N questions


class PrivacyStats:
    def __init__(self):
        self.total_processed = 0
        self.pii_detected = 0
        self.non_pii = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.response_times = []
        self.last_save_point = 0

        # Pass the created NLP engine and supported_languages to the AnalyzerEngine
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine_with_french, supported_languages=["fr"]
        )
        self.batch_analyzer = BatchAnalyzerEngine(analyzer_engine=self.analyzer)
        self.anonymizer = AnonymizerEngine()
        self.stats = PrivacyStats()
        self.output_dir = Path("results")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_result(self, pii_present: bool, time_taken: float):
        self.total_processed += 1
        if pii_present:
            self.pii_detected += 1
        else:
            self.non_pii += 1
        self.response_times.append(time_taken)

    def add_error(self):
        self.errors += 1
        self.total_processed += 1

    def should_save(self) -> bool:
        return (self.total_processed - self.last_save_point) >= Config.SAVE_INTERVAL

    def update_save_point(self):
        self.last_save_point = self.total_processed

    def get_summary(self) -> Dict:
        end_time = datetime.now()
        return {
            "total_processed": self.total_processed,
            "pii_detected": self.pii_detected,
            "non_pii": self.non_pii,
            "error_count": self.errors,
            "avg_response_time": (
                (sum(self.response_times) / len(self.response_times))
                if self.response_times
                else 0
            ),
            "total_time": str(end_time - self.start_time),
            "timestamp": end_time.isoformat(),
        }

    def analyze_text(self, text: str) -> List:
        return self.analyzer.analyze(text=text, language=Config.LANGUAGE)

    def anonymize_text(self, text: str, recognizer_results: List) -> str:
        return self.anonymizer.anonymize(
            text=text, analyzer_results=recognizer_results
        ).text

    # def analyze_text(self, text: str) -> Optional[List[dict]]:
    #     payload = {
    #         "text": text,
    #         "language": Config.LANGUAGE
    #     }
    #     result = self._call_api(Config.ANALYZE_URL, payload)
    #     return result if result else None

    # def anonymize_text(self, text: str, analyzer_results: List[dict]) -> Optional[str]:
    #     payload = {
    #         "text": text,
    #         "analyzer_results": analyzer_results
    #     }
    #     result = self._call_api(Config.ANONYMIZE_URL, payload)
    #     return result.get("text") if result else None

    def process_batch(self, batch: List[Dict]) -> List[Dict]:
        results = []
        for item in tqdm(
            batch,
            desc=f"Processing batch {self.stats.total_processed//Config.BATCH_SIZE + 1}",
        ):
            text = item["question_content"]
            start_time = time.time()

            try:
                # Analyze text
                analysis_result = self.analyze_text(text)
                if analysis_result is None:
                    raise ValueError("Analysis API failed")

                pii_present = len(analysis_result) > 0
                elapsed = time.time() - start_time

                # Anonymize if PII found
                anonymized_text = text
                if pii_present:
                    anonymized = self.anonymize_text(text, analysis_result)
                    if anonymized:
                        anonymized_text = anonymized

                self.stats.add_result(pii_present, elapsed)

                results.append(
                    {
                        "text": text,
                        "anonymized_text": anonymized_text,
                        "pii_present": pii_present,
                        "question_id": item.get("question_id", "unknown"),
                    }
                )

            except Exception as e:
                logger.error(f"Error processing item: {str(e)}")
                self.stats.add_error()
                results.append(
                    {
                        "text": text,
                        "anonymized_text": "ERROR",
                        "pii_present": "error",
                        "question_id": item.get("question_id", "unknown"),
                    }
                )

            if self.stats.should_save():
                self.save_results(pd.DataFrame(results), is_final=False)
                self.stats.update_save_point()

        return results

    def process_dataset(
        self, hf_token: str, num_samples: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        try:
            ds = load_dataset("ministere-culture/comparia-questions", token=hf_token)
            total_available = len(ds["train"])

            num_samples = num_samples or Config.DEFAULT_SAMPLE_SIZE or total_available
            num_samples = min(num_samples, total_available)

            logger.info(f"Processing {num_samples} out of {total_available} questions")

            all_results = []
            for i in range(0, num_samples, Config.BATCH_SIZE):
                batch_size = min(Config.BATCH_SIZE, num_samples - i)
                batch = ds["train"].select(range(i, i + batch_size))
                batch_results = self.process_batch(batch)
                all_results.extend(batch_results)

            return pd.DataFrame(all_results)

        except Exception as e:
            logger.error(f"Error processing dataset: {str(e)}")
            return None

    def save_results(self, df: pd.DataFrame, is_final: bool = True):
        """Save results and statistics"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "final" if is_final else f"batch_{self.stats.total_processed}"

        df.to_csv(
            self.output_dir / f"{prefix}_privacy_analysis_{timestamp}.csv", index=False
        )

        if is_final or self.stats.should_save():
            stats = self.stats.get_summary()
            with open(
                self.output_dir / f"{prefix}_statistics_{timestamp}.json", "w"
            ) as f:
                json.dump(stats, f, indent=2)

            summary = pd.DataFrame(
                [
                    {
                        "Total Processed": stats["total_processed"],
                        "PII Detected": stats["pii_detected"],
                        "Non-PII": stats["non_pii"],
                        "Errors": stats["error_count"],
                        "Avg Response Time": f"{stats['avg_response_time']:.2f}s",
                        "Total Time": stats["total_time"],
                    }
                ]
            )

            summary.to_csv(
                self.output_dir / f"{prefix}_summary_{timestamp}.csv", index=False
            )

            if is_final:
                logger.info(f"\nFinal results saved to {self.output_dir}")
            else:
                logger.info(
                    f"\nIntermediate results saved at {self.stats.total_processed} questions"
                )


def main():
    parser = argparse.ArgumentParser(description="Privacy classifier using Presidio")
    parser.add_argument(
        "--samples",
        type=int,
        default=Config.DEFAULT_SAMPLE_SIZE,
        help="Number of samples to process (default: all)",
    )
    parser.add_argument(
        "--output", type=str, default="results", help="Output directory"
    )
    parser.add_argument("--token", type=str, help="Hugging Face token")

    args = parser.parse_args()

    hf_token = args.token
    if not hf_token:
        print("\nHugging Face token is required to access the dataset.")
        print("You can find your token at: https://huggingface.co/settings/tokens")
        hf_token = input("Please enter your Hugging Face token: ").strip()

    classifier = PrivacyClassifier(output_dir=args.output)
    df = classifier.process_dataset(hf_token=hf_token, num_samples=args.samples)
    if df is not None:
        classifier.save_results(df, is_final=True)


if __name__ == "__main__":
    main()
