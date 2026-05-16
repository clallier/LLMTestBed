"""
Security Model Benchmark Script.

High level role: Evaluates the performance and accuracy of the Bayesian 
classifier using the 'test' split of the corpus.
"""
import os
import json
import time
from typing import List, Dict, Any
from backend.security.preprocessor import SecurityPreprocessor

def run_test():
    """Runs the benchmark suite against the test split."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    corpus_path = os.path.join(current_dir, "corpus.json")
    
    with open(corpus_path, 'r') as f:
        data = json.load(f)
        
    test_data = [item for item in data if item.get('split') == 'test']
    engine = SecurityPreprocessor()
    
    print(f"📊 Running Benchmark on {len(test_data)} test cases...")
    print("-" * 80)
    print(f"{'Target':<10} | {'Risk':<7} | {'Latency':<8} | {'Status':<8} | {'Text'}")
    print("-" * 80)
    
    results = []
    for item in test_data:
        res = _evaluate_case(item, engine)
        results.append(res)
        _print_row(res)

    _print_summary(results)

def _evaluate_case(item: Dict[str, Any], engine: SecurityPreprocessor) -> Dict[str, Any]:
    """Evaluates a single test case."""
    start_time = time.perf_counter()
    risk_score = engine.calculate_risk(item['text'])
    latency = (time.perf_counter() - start_time) * 1000
    
    is_injection = item['label'] == 'injection'
    is_correct = (risk_score >= 0.5) == is_injection
    
    return {
        "text": item['text'],
        "label": item['label'],
        "score": risk_score,
        "latency": latency,
        "correct": is_correct
    }

def _print_row(res: Dict[str, Any]):
    """Prints a single result row."""
    status = "✅ PASS" if res['correct'] else "❌ FAIL"
    color_score = f"{res['score']*100:>5.1f}%"
    print(f"{res['label']:<10} | {color_score} | {res['latency']:>6.2f}ms | {status:<8} | {res['text'][:40]}")

def _print_summary(results: List[Dict[str, Any]]):
    """Prints the final summary statistics."""
    total = len(results)
    correct = sum(1 for r in results if r['correct'])
    avg_latency = sum(r['latency'] for r in results) / total
    
    print("-" * 80)
    print(f"📈 Summary: {correct}/{total} correct ({correct/total*100:.1f}%)")
    print(f"⏱️ Average Latency: {avg_latency:.2f}ms")
    print("-" * 80)

if __name__ == "__main__":
    run_test()
