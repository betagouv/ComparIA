import json
import argparse
from pathlib import Path
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime
from tqdm import tqdm
import pandas as pd
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from datasets import load_dataset


class Config:
    PROJECT_ID = "languia-430909"  # Update with your GCP project ID
    LOCATION = "europe-west1"                 # Update with your preferred location
    MODEL_NAME = "gemini-2.0-flash-001"
    MAX_RETRIES = 3
    RETRY_DELAY = 1
    
    # Dataset settings
    BATCH_SIZE = 50
    DEFAULT_SAMPLE_SIZE = None
    SAVE_INTERVAL = 50
    
    TEST_CASES = [
        ("Je m'appelle Jean Dupont et mon email est jean.dupont@email.fr", True, "Contient nom et email"),
        ("Il fait beau aujourd'hui à Paris", False, "Pas d'information personnelle"),
        ("Mon numéro de sécurité sociale est 1 85 12 35 123 456 12", True, "Contient numéro de sécurité sociale")
    ]
        
    PROMPT_TEMPLATE = (
        "Task: Identify if text contains personal, sensitive, or private information.\n"
        "Rules:\n"
        "- Answer ONLY with single word 'true' or 'false'\n"
        "- true = contains personal info (names, emails, addresses) or sensitive info (medical, financial)\n"
        "- false = no personal or sensitive info\n\n"
        "Text: {text}\n"
        "Answer: "
    )

class PrivacyStats:
    def __init__(self):
        self.total_processed = 0
        self.sensitive_count = 0
        self.non_sensitive_count = 0
        self.errors = 0
        self.start_time = datetime.now()
        self.response_times = []
        self.last_save_point = 0
    
    def add_result(self, is_sensitive: bool, time_taken: float):
        self.total_processed += 1
        if is_sensitive:
            self.sensitive_count += 1
        else:
            self.non_sensitive_count += 1
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
            "sensitive_count": self.sensitive_count,
            "non_sensitive_count": self.non_sensitive_count,
            "error_count": self.errors,
            "avg_response_time": sum(self.response_times) / len(self.response_times) if self.response_times else 0,
            "total_time": str(end_time - self.start_time),
            "timestamp": end_time.isoformat()
        }

class PrivacyClassifier:
    def __init__(self, output_dir: str = 'results'):
        self.stats = PrivacyStats()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_logging()
        self.model = self._initialize_model()
        
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
    
    def _initialize_model(self):
        """Initialize Vertex AI and load the model"""
        try:
            vertexai.init(project=Config.PROJECT_ID, location=Config.LOCATION)
            return GenerativeModel(Config.MODEL_NAME)
        except Exception as e:
            self.logger.error(f"Model initialization failed: {str(e)}")
            return None
    
    def setup(self) -> bool:
        """Verify model accessibility"""
        if not self.model:
            return False
        return self._run_tests()
    
    def _run_tests(self) -> bool:
        """Run test cases to verify model behavior"""
        self.logger.info("\nRunning test cases...")
        passed = 0
        
        for text, expected, desc in Config.TEST_CASES:
            self.logger.info(f"\nTest case: {desc}")
            self.logger.info(f"Text: '{text}'")
            
            result = self._get_classification(text)
            if result is not None and result == expected:
                passed += 1
                self.logger.info("✓ Test passed")
            else:
                self.logger.warning(f"✗ Test failed (expected {expected}, got {result})")
        
        success_rate = passed / len(Config.TEST_CASES)
        self.logger.info(f"\nTests passed: {passed}/{len(Config.TEST_CASES)} ({success_rate:.0%})")
        
        if success_rate < 0.75:
            proceed = input("\n❗ Model accuracy is low. Proceed anyway? (yes/no): ").lower().strip()
            return proceed == 'yes'
        return True

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
                    self.stats.add_result(result, elapsed)
                    return result
                else:
                    self.logger.warning(f"Unexpected response: {response.text}")
                    
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < Config.MAX_RETRIES - 1:
                    time.sleep(Config.RETRY_DELAY)
        
        self.stats.add_error()
        return None
    
    def process_batch(self, batch: List[Dict]) -> List[Dict]:
        """Process a batch of questions"""
        results = []
        for item in tqdm(batch, desc=f"Processing batch {self.stats.total_processed//Config.BATCH_SIZE + 1}"):
            text = item['question_content']
            result = self._get_classification(text)
            
            results.append({
                'text': text,
                'contains_sensitive_info': result if result is not None else 'error',
                'question_id': item.get('question_id', 'unknown')
            })
            
            if self.stats.should_save():
                self.save_results(pd.DataFrame(results), is_final=False)
                self.stats.update_save_point()
                
        return results

    def process_dataset(self, hf_token: str, num_samples: Optional[int] = None) -> Optional[pd.DataFrame]:
        """Process dataset with batch processing"""
        try:
            ds = load_dataset("ministere-culture/comparia-questions", token=hf_token)
            total_available = len(ds['train'])
            
            num_samples = num_samples or Config.DEFAULT_SAMPLE_SIZE or total_available
            num_samples = min(num_samples, total_available)
            
            self.logger.info(f"Processing {num_samples} out of {total_available} questions")
            
            all_results = []
            for i in range(0, num_samples, Config.BATCH_SIZE):
                batch_size = min(Config.BATCH_SIZE, num_samples - i)
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
                'Contains Sensitive Info': stats['sensitive_count'],
                'No Sensitive Info': stats['non_sensitive_count'],
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
    parser = argparse.ArgumentParser(description='Privacy classifier using Ollama')
    parser.add_argument('--samples', type=int, default=Config.DEFAULT_SAMPLE_SIZE, 
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
    # if not classifier.setup():
    #     return
    
    df = classifier.process_dataset(hf_token=hf_token, num_samples=args.samples)
    if df is not None:
        classifier.save_results(df, is_final=True)

if __name__ == "__main__":
    main()
