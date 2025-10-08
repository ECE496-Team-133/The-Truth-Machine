#!/usr/bin/env python3
"""
Test the full local system against the test dataset.
This runs the complete original pipeline but with local models instead of OpenAI.
"""

import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.local_openai_client import LocalOpenAIClient, set_local_openai_client
from utils.local_claims import extract_claims_from_query, optimize_claim, get_query_for_wiki_article
from utils.google_custom_search import get_first_n_results_urls
from utils.wikipedia_scraper import scrape_wikipedia_content
from utils.local_factcheck_full import find_answer_in_article, build_text_fragment_link


class FullLocalTestRunner:
    """Test runner for the full local system."""
    
    def __init__(self, base_url: str = "http://localhost:1234", model: str = "local-model"):
        self.base_url = base_url
        self.model = model
        
        # Set up local client
        local_client = LocalOpenAIClient(base_url, model)
        set_local_openai_client(local_client)
        
        print(f"Using local model at {base_url} with model '{model}'")
    
    def load_test_dataset(self, dataset_name: str = "test_claims_wikipedia") -> List[Dict[str, Any]]:
        """Load test dataset."""
        dataset_path = Path(f"src/data/{dataset_name}.jsonl")
        dataset = []
        
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    dataset.append(json.loads(line))
        
        return dataset
    
    def test_single_claim(self, test_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test a single claim using the full local system."""
        start_time = time.time()
        
        test_id = test_data['id']
        claim = test_data['claim']
        expected_label = test_data['expected_label']
        
        print(f"\nProcessing test {test_id}: {claim}")
        
        result = {
            'test_id': test_id,
            'claim': claim,
            'expected_label': expected_label,
            'predicted_label': None,
            'evidence': None,
            'is_correct': False,
            'processing_time': 0,
            'error': None,
            'article_query': None,
            'urls': []
        }
        
        try:
            # Step 1: Optimize claim
            print(f"  Optimizing claim...")
            optimized_claim = optimize_claim(claim)
            print(f"  Optimized: {optimized_claim}")
            
            # Step 2: Get Wikipedia article query
            print(f"  Getting Wikipedia query...")
            article_query = get_query_for_wiki_article(claim)
            result['article_query'] = article_query
            print(f"  Query: {article_query}")
            
            # Step 3: Get URLs
            print(f"  Fetching URLs...")
            urls = get_first_n_results_urls(article_query, 1)
            result['urls'] = urls
            print(f"  URLs: {urls}")
            
            if not urls:
                result['error'] = "No URLs found"
                return result
            
            # Step 4: Scrape content
            print(f"  Scraping content...")
            content = scrape_wikipedia_content(urls[0])
            if not content:
                result['error'] = "Failed to scrape content"
                return result
            
            print(f"  Scraped {len(content)} characters")
            
            # Step 5: Fact-check
            print(f"  Fact-checking...")
            factcheck_result = find_answer_in_article(content, claim)
            
            if factcheck_result:
                result['predicted_label'] = factcheck_result.label
                result['evidence'] = factcheck_result.evidence
                result['is_correct'] = (result['predicted_label'] == expected_label)
                print(f"  Predicted: {result['predicted_label']}, Expected: {expected_label}, Correct: {result['is_correct']}")
            else:
                result['error'] = "Failed to get factcheck result"
            
        except Exception as e:
            result['error'] = str(e)
            print(f"  Error: {e}")
        
        result['processing_time'] = time.time() - start_time
        return result
    
    def run_tests(self, max_tests: int = None, dataset_name: str = "test_claims_wikipedia") -> List[Dict[str, Any]]:
        """Run tests on the dataset."""
        print(f"Loading test dataset: {dataset_name}")
        dataset = self.load_test_dataset(dataset_name)
        
        if max_tests:
            dataset = dataset[:max_tests]
        
        print(f"Running {len(dataset)} tests with full local system...")
        
        results = []
        for i, test_data in enumerate(dataset, 1):
            print(f"\n{'='*60}")
            print(f"Test {i}/{len(dataset)}")
            print(f"{'='*60}")
            
            result = self.test_single_claim(test_data)
            results.append(result)
        
        return results
    
    def calculate_score(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate accuracy score and other metrics."""
        total_tests = len(results)
        correct_tests = sum(1 for r in results if r['is_correct'])
        accuracy = correct_tests / total_tests if total_tests > 0 else 0.0
        
        # Calculate per-label accuracy
        true_expected = [r for r in results if r['expected_label'] == "True"]
        false_expected = [r for r in results if r['expected_label'] == "False"]
        
        true_correct = sum(1 for r in true_expected if r['is_correct'])
        false_correct = sum(1 for r in false_expected if r['is_correct'])
        
        true_accuracy = true_correct / len(true_expected) if true_expected else 0.0
        false_accuracy = false_correct / len(false_expected) if false_expected else 0.0
        
        # Calculate timing statistics
        processing_times = [r['processing_time'] for r in results if r['processing_time'] > 0]
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
        
        # Count errors
        error_count = sum(1 for r in results if r['error'] is not None)
        
        return {
            'total_tests': total_tests,
            'correct_tests': correct_tests,
            'accuracy': accuracy,
            'true_expected_count': len(true_expected),
            'true_correct_count': true_correct,
            'true_accuracy': true_accuracy,
            'false_expected_count': len(false_expected),
            'false_correct_count': false_correct,
            'false_accuracy': false_accuracy,
            'error_count': error_count,
            'avg_processing_time': avg_processing_time
        }
    
    def print_results(self, results: List[Dict[str, Any]], score: Dict[str, Any]):
        """Print detailed results."""
        print(f"\n{'='*60}")
        print("FULL LOCAL SYSTEM TEST RESULTS")
        print(f"{'='*60}")
        print(f"Total Tests: {score['total_tests']}")
        print(f"Correct: {score['correct_tests']}")
        print(f"Accuracy: {score['accuracy']:.2%}")
        print(f"Errors: {score['error_count']}")
        print(f"Average Processing Time: {score['avg_processing_time']:.2f}s")
        
        print(f"\nPer-Label Accuracy:")
        print(f"True Claims: {score['true_correct_count']}/{score['true_expected_count']} ({score['true_accuracy']:.2%})")
        print(f"False Claims: {score['false_correct_count']}/{score['false_expected_count']} ({score['false_accuracy']:.2%})")
        
        print(f"\nDetailed Results:")
        print(f"{'ID':<4} {'Expected':<8} {'Predicted':<10} {'Correct':<8} {'Time':<8} {'Error':<20}")
        print("-" * 70)
        
        for result in sorted(results, key=lambda x: x['test_id']):
            error_str = result['error'][:17] + "..." if result['error'] and len(result['error']) > 20 else (result['error'] or "")
            print(f"{result['test_id']:<4} {result['expected_label']:<8} {result['predicted_label'] or 'None':<10} {result['is_correct']!s:<8} {result['processing_time']:.2f}s {error_str:<20}")
    
    def save_results(self, results: List[Dict[str, Any]], score: Dict[str, Any], output_path: str):
        """Save results to JSON file."""
        output_data = {
            'summary': score,
            'results': results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_path}")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test full local system against dataset")
    parser.add_argument('--base-url', default='http://localhost:1234', help='Base URL for local model')
    parser.add_argument('--model', default='local-model', help='Model name')
    parser.add_argument('--max-tests', type=int, help='Maximum number of tests to run')
    parser.add_argument('--dataset', default='test_claims_wikipedia', help='Dataset to use (without .jsonl extension)')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print("Full Local System Test")
    print("=" * 40)
    print("This runs the complete original pipeline with local models:")
    print("1. Extract claims from query")
    print("2. Optimize claims")
    print("3. Get Wikipedia article queries")
    print("4. Search Google for URLs")
    print("5. Scrape Wikipedia content")
    print("6. Fact-check using local model")
    print("7. Compare with expected results")
    print()
    
    # Create test runner
    runner = FullLocalTestRunner(args.base_url, args.model)
    
    # Run tests
    results = runner.run_tests(max_tests=args.max_tests, dataset_name=args.dataset)
    
    # Calculate and display results
    score = runner.calculate_score(results)
    runner.print_results(results, score)
    
    # Save results if requested
    if args.output:
        runner.save_results(results, score, args.output)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
