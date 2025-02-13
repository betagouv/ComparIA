# Presidio settings
LANGUAGE = "fr"
import json
import requests
from datasets import load_dataset
import argparse
from pathlib import Path
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from tqdm import tqdm
import pandas as pd
import math

from presidio_analyzer import AnalyzerEngine, BatchAnalyzerEngine, RecognizerResult, DictAnalyzerResult
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
            "avg_response_time": (sum(self.response_times) / len(self.response_times)) if self.response_times else 0,
            "total_time": str(end_time - self.start_time),
            "timestamp": end_time.isoformat()
        }

class PrivacyClassifier:
    def __init__(self, output_dir: str = 'results'):
        self.analyzer = AnalyzerEngine()
        self.batch_analyzer = BatchAnalyzerEngine(analyzer_engine=self.analyzer)
        self.anonymizer = AnonymizerEngine()
        self.stats = PrivacyStats()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.output_dir / 'privacy_classifier.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def analyze_text(self, text: str) -> List:
        return self.analyzer.analyze(text=text, language=Config.LANGUAGE)

    def anonymize_text(self, text: str, recognizer_results: List) -> str:
        return self.anonymizer.anonymize(text=text, analyzer_results=recognizer_results).text

    def process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of questions"""
        results = []
        for item in tqdm(batch, desc=f"Processing batch {self.stats.total_processed//BATCH_SIZE + 1}"):
            text = item['question_content']
            result_list = self.analyze_text(text)
            pii_present = bool(result_list)

            # Optional: Replace PII with anonymized content
            if pii_present:
                anonymized_text = self.anonymize_text(text, result_list)
            else:
                anonymized_text = text

            results.append({
                'text': text,
                'anonymized_text': anonymized_text,
                'pii_present': pii_present,
                'question_id': item.get('question_id', 'unknown')
            })

            if self.stats.should_save():
                self.save_results(pd.DataFrame(results), is_final=False)
                self.stats.update_save_point()

        return results

    def process_dataset(self, hf_token: str, num_samples: Optional[int] = None) -> Optional[pd.DataFrame]:
        try:
            ds = load_dataset("ministere-culture/comparia-questions", token=hf_token)
            total_available = len(ds['train'])

            num_samples = num_samples or DEFAULT_SAMPLE_SIZE or total_available
            num_samples = min(num_samples, total_available)

            self.logger.info(f"Processing {num_samples} out of {total_available} questions")

            all_results = []
            for i in range(0, num_samples, BATCH_SIZE):
                batch_size = min(BATCH_SIZE, num_samples - i)
                batch = ds['train'].select(range(i, i + batch_size))
                batch_results = self.process_batch(batch)
                all_results.extend(batch_results)

            return pd.DataFrame(all_results)

        except Exception as e:
            self.logger.error(f"Error processing dataset: {str(e)}")
            return None

    def save_results(self, df: pd.DataFrame, is_final: bool = True):
        """Save results and statistics"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = 'final' if is_final else f'batch_{self.stats.total_processed}'

        df.to_csv(self.output_dir / f'{prefix}_privacy_analysis_{timestamp}.csv', index=False)

        if is_final or self.stats.should_save():
            stats = self.stats.get_summary()
            with open(self.output_dir / f'{prefix}_statistics_{timestamp}.json', 'w') as f:
                json.dump(stats, f, indent=2)

            summary = pd.DataFrame([{
                'Total Processed': stats['total_processed'],
                'PII Detected': stats['pii_detected'],
                'Non-PII': stats['non_pii'],
                'Errors': stats['error_count'],
                'Avg Response Time': f"{stats['avg_response_time']:.2f}s",
                'Total Time': stats['total_time']
            }])

            summary.to_csv(self.output_dir / f'{prefix}_summary_{timestamp}.csv', index=False)

            if is_final:
                self.logger.info(f"\nFinal results saved to {self.output_dir}")
            else:
                self.logger.info(f"\nIntermediate results saved at {self.stats.total_processed} questions")

def main():
    parser = argparse.ArgumentParser(description='Privacy classifier using Presidio')
    parser.add_argument('--samples', type=int, default=DEFAULT_SAMPLE_SIZE, 
                        help='Number of samples to process (default: all)')
    parser.add_argument('--output', type=str, default='results', help='Output directory')
    parser.add_argument('--token', type=str, help='Hugging Face token')
    
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