#!/usr/bin/env python3
"""
Performance Testing and Simulation Script
==========================================

This script demonstrates the performance tracking capabilities by:
1. Recording simulated predictions
2. Providing true labels
3. Calculating performance metrics
4. Detecting model drift
5. Exporting results to CSV

Usage:
    python scripts/performance_test.py [--api-url] [--mode] [--count]

Examples:
    # Simulate predictions locally
    python scripts/performance_test.py --mode local --count 100
    
    # Test against running API
    python scripts/performance_test.py --api-url http://localhost:8000 --count 50
    
    # Run full demo with drift
    python scripts/performance_test.py --api-url http://localhost:8000 --mode drift-demo
"""

import argparse
import json
import random
import time
import csv
from datetime import datetime
from pathlib import Path
import sys
import requests

# Add parent directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.performance import tracker
    LOCAL_MODE_AVAILABLE = True
except ImportError:
    LOCAL_MODE_AVAILABLE = False


# Color output for better readability
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.RESET}")


def print_metric(label, value):
    print(f"  {label:<30} {Colors.BOLD}{value}{Colors.RESET}")


# ============================================================================
# Local Testing Mode
# ============================================================================

def simulate_predictions_local(count=100, drift_mode=False):
    """Simulate predictions locally using the tracker directly."""
    print_header("LOCAL SIMULATION MODE")
    print_info(f"Simulating {count} predictions locally...\n")
    
    classes = ["cat", "dog"]
    prediction_ids = []
    
    # Phase 1: Record predictions
    print(f"{Colors.BOLD}Phase 1: Recording Predictions{Colors.RESET}")
    for i in range(count):
        # In drift mode, gradually reduce accuracy in second half
        if drift_mode and i >= count // 2:
            # Random predictions (50% accuracy)
            predicted_class = random.choice(classes)
            true_label = random.choice(classes)
            confidence = random.uniform(0.4, 0.7)
        else:
            # Good predictions (80-90% accuracy)
            true_label = random.choice(classes)
            # 85% of time predict correctly
            if random.random() < 0.85:
                predicted_class = true_label
                confidence = random.uniform(0.85, 0.99)
            else:
                predicted_class = "dog" if true_label == "cat" else "cat"
                confidence = random.uniform(0.4, 0.6)
        
        # Record prediction
        pred_id = tracker.record_prediction(
            predicted_class=predicted_class,
            confidence=confidence,
            model_version="v1.0",
            inference_time_ms=random.uniform(50, 200),
        )
        prediction_ids.append((pred_id, true_label))
        
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  Recorded {i + 1}/{count} predictions...", end="\r")
    
    print(f"  Recorded {count}/{count} predictions      ")
    print_success(f"All {count} predictions recorded\n")
    
    # Phase 2: Provide true labels
    print(f"{Colors.BOLD}Phase 2: Providing True Labels{Colors.RESET}")
    labeled_count = 0
    for pred_id, true_label in prediction_ids:
        # Label 80% of predictions to simulate real-world scenario
        if random.random() < 0.8:
            tracker.provide_true_label(pred_id, true_label)
            labeled_count += 1
        
        if labeled_count % 20 == 0:
            print(f"  Labeled {labeled_count} predictions...", end="\r")
    
    print(f"  Labeled {labeled_count} predictions      ")
    print_success(f"{labeled_count}/{count} predictions labeled\n")
    
    return prediction_ids


def show_metrics_local():
    """Display performance metrics from local tracker."""
    print_header("PERFORMANCE METRICS")
    
    metrics = tracker.calculate_metrics()
    
    # Basic stats
    print(f"{Colors.BOLD}Basic Statistics:{Colors.RESET}")
    print_metric("Total Predictions", metrics.get("total_predictions", 0))
    print_metric("Labeled Predictions", metrics.get("labeled_predictions", 0))
    print_metric("Overall Accuracy", f"{metrics.get('accuracy', 0):.2%}")
    
    # Confidence stats
    print(f"\n{Colors.BOLD}Confidence Statistics:{Colors.RESET}")
    conf_stats = metrics.get("confidence_stats", {})
    print_metric("Avg Confidence (All)", f"{conf_stats.get('avg_confidence', 0):.4f}")
    print_metric("Avg Confidence (Correct)", f"{conf_stats.get('avg_confidence_correct', 0):.4f}")
    print_metric("Avg Confidence (Incorrect)", f"{conf_stats.get('avg_confidence_incorrect', 0):.4f}")
    
    # Per-class metrics
    print(f"\n{Colors.BOLD}Per-Class Metrics:{Colors.RESET}")
    per_class = metrics.get("per_class_metrics", {})
    for class_name, class_metrics in per_class.items():
        print(f"\n  {Colors.BOLD}{class_name.upper()}{Colors.RESET}")
        print_metric("    Precision", f"{class_metrics.get('precision', 0):.4f}")
        print_metric("    Recall", f"{class_metrics.get('recall', 0):.4f}")
        print_metric("    F1-Score", f"{class_metrics.get('f1', 0):.4f}")
        print_metric("    TP/FP/FN", f"{class_metrics.get('tp', 0)}/{class_metrics.get('fp', 0)}/{class_metrics.get('fn', 0)}")
    
    # Confusion matrix
    print(f"\n{Colors.BOLD}Confusion Matrix:{Colors.RESET}")
    conf_matrix = metrics.get("confusion_matrix", {})
    if conf_matrix:
        for true_label, predictions in conf_matrix.items():
            print(f"  True: {true_label:6} → {predictions}")
    
    print()


def show_drift_indicators_local(window_size=100):
    """Display drift detection indicators."""
    print_header("DRIFT DETECTION")
    
    drift = tracker.get_drift_indicators(window_size)
    
    print_metric("Drift Detected", Colors.RED + "YES" + Colors.RESET if drift.get("drift_detected") else Colors.GREEN + "NO" + Colors.RESET)
    print_metric("Window Size", window_size)
    
    if drift.get("reasons"):
        print(f"\n{Colors.BOLD}Drift Reasons:{Colors.RESET}")
        for reason in drift.get("reasons", []):
            print(f"  • {reason}")
    
    # Recent vs older window comparison
    print(f"\n{Colors.BOLD}Recent Window (last {window_size}):{Colors.RESET}")
    recent = drift.get("recent_window", {})
    print_metric("  Accuracy", f"{recent.get('accuracy', 0):.2%}")
    print_metric("  Avg Confidence", f"{recent.get('avg_confidence', 0):.4f}")
    print_metric("  Sample Count", recent.get('count', 0))
    
    print(f"\n{Colors.BOLD}Older Window (before recent):{Colors.RESET}")
    older = drift.get("older_window", {})
    print_metric("  Accuracy", f"{older.get('accuracy', 0):.2%}")
    print_metric("  Avg Confidence", f"{older.get('avg_confidence', 0):.4f}")
    print_metric("  Sample Count", older.get('count', 0))
    
    # Changes
    print(f"\n{Colors.BOLD}Changes:{Colors.RESET}")
    print_metric("  Accuracy Change", f"{drift.get('accuracy_change', 0):.2%}")
    print_metric("  Confidence Change", f"{drift.get('confidence_change', 0):.4f}")
    
    print()


def export_predictions_local(output_file="predictions.csv"):
    """Export predictions to CSV."""
    print_header("EXPORT PREDICTIONS")
    
    filepath = tracker.save_to_csv(output_file)
    print_success(f"Predictions exported to: {Colors.BOLD}{filepath}{Colors.RESET}")
    
    # Show file stats
    try:
        file_path = Path(filepath)
        file_size = file_path.stat().st_size / 1024  # KB
        with open(filepath, 'r') as f:
            row_count = sum(1 for _ in f) - 1  # Exclude header
        print_metric("File Size", f"{file_size:.2f} KB")
        print_metric("Records Exported", row_count)
    except Exception as e:
        print_error(f"Could not read file stats: {e}")
    
    print()


# ============================================================================
# API Testing Mode
# ============================================================================

def test_api_endpoints(api_url, count=50, drift_mode=False):
    """Test performance tracking via API endpoints."""
    print_header("API TESTING MODE")
    print_info(f"Testing API at {Colors.BOLD}{api_url}{Colors.RESET}\n")
    
    # Check if API is running
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        print_success("API is accessible")
    except Exception as e:
        print_error(f"Cannot reach API: {e}")
        return
    
    classes = ["cat", "dog"]
    prediction_ids = []
    
    # Phase 1: Record predictions via API
    print(f"\n{Colors.BOLD}Phase 1: Recording Predictions via API{Colors.RESET}")
    for i in range(count):
        # In drift mode, gradually reduce accuracy in second half
        if drift_mode and i >= count // 2:
            predicted_class = random.choice(classes)
            confidence = random.uniform(0.4, 0.7)
            true_label = random.choice(classes)
        else:
            true_label = random.choice(classes)
            if random.random() < 0.85:
                predicted_class = true_label
                confidence = random.uniform(0.85, 0.99)
            else:
                predicted_class = "dog" if true_label == "cat" else "cat"
                confidence = random.uniform(0.4, 0.6)
        
        try:
            response = requests.post(
                f"{api_url}/predictions/record",
                json={
                    "predicted_class": predicted_class,
                    "confidence": confidence,
                    "model_version": "v1.0",
                    "inference_time_ms": random.uniform(50, 200),
                },
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                pred_id = data.get("prediction_id")
                prediction_ids.append((pred_id, true_label))
            
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  Recorded {i + 1}/{count} predictions...", end="\r")
        except Exception as e:
            print_error(f"Failed to record prediction: {e}")
            break
    
    if prediction_ids:
        print(f"  Recorded {len(prediction_ids)}/{count} predictions      ")
        print_success(f"All {len(prediction_ids)} predictions recorded")
    
    # Phase 2: Provide true labels via API
    print(f"\n{Colors.BOLD}Phase 2: Providing True Labels via API{Colors.RESET}")
    labeled_count = 0
    for pred_id, true_label in prediction_ids:
        # Label 80% of predictions
        if random.random() < 0.8:
            try:
                response = requests.post(
                    f"{api_url}/predictions/{pred_id}/label",
                    json={"true_label": true_label},
                    timeout=5
                )
                if response.status_code == 200:
                    labeled_count += 1
            except Exception as e:
                print_error(f"Failed to provide true label: {e}")
                break
            
            if labeled_count % 10 == 0:
                print(f"  Labeled {labeled_count} predictions...", end="\r")
    
    print(f"  Labeled {labeled_count} predictions      ")
    print_success(f"{labeled_count}/{len(prediction_ids)} predictions labeled")


def get_api_metrics(api_url):
    """Get metrics from API endpoint."""
    print_header("PERFORMANCE METRICS (from API)")
    
    try:
        response = requests.get(f"{api_url}/performance/metrics", timeout=5)
        if response.status_code == 200:
            metrics = response.json()
            
            # Basic stats
            print(f"{Colors.BOLD}Basic Statistics:{Colors.RESET}")
            print_metric("Total Predictions", metrics.get("total_predictions", 0))
            print_metric("Labeled Predictions", metrics.get("labeled_predictions", 0))
            print_metric("Overall Accuracy", f"{metrics.get('accuracy', 0):.2%}")
            
            # Per-class metrics
            print(f"\n{Colors.BOLD}Per-Class Metrics:{Colors.RESET}")
            per_class = metrics.get("per_class_metrics", {})
            for class_name, class_metrics in per_class.items():
                print(f"\n  {Colors.BOLD}{class_name.upper()}{Colors.RESET}")
                print_metric("    Precision", f"{class_metrics.get('precision', 0):.4f}")
                print_metric("    Recall", f"{class_metrics.get('recall', 0):.4f}")
                print_metric("    F1-Score", f"{class_metrics.get('f1', 0):.4f}")
            
            print()
        else:
            print_error(f"API returned status {response.status_code}")
    except Exception as e:
        print_error(f"Failed to get metrics: {e}")


def get_api_drift(api_url, window_size=100):
    """Get drift indicators from API endpoint."""
    print_header("DRIFT DETECTION (from API)")
    
    try:
        response = requests.get(
            f"{api_url}/performance/drift",
            params={"window_size": window_size},
            timeout=5
        )
        if response.status_code == 200:
            drift = response.json()
            
            print_metric("Drift Detected", 
                        Colors.RED + "YES" + Colors.RESET if drift.get("drift_detected") else Colors.GREEN + "NO" + Colors.RESET)
            
            if drift.get("reasons"):
                print(f"\n{Colors.BOLD}Drift Reasons:{Colors.RESET}")
                for reason in drift.get("reasons", []):
                    print(f"  • {reason}")
            
            print()
        else:
            print_error(f"API returned status {response.status_code}")
    except Exception as e:
        print_error(f"Failed to get drift indicators: {e}")


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Performance Testing Script for Cats vs Dogs Model",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Local simulation with 100 predictions
  python scripts/performance_test.py --mode local --count 100
  
  # Local simulation with drift in second half
  python scripts/performance_test.py --mode local --drift-demo
  
  # Test against running API
  python scripts/performance_test.py --api-url http://localhost:8000 --count 50
  
  # Test API with drift simulation
  python scripts/performance_test.py --api-url http://localhost:8000 --drift-demo
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["local", "api"],
        default="local",
        help="Testing mode (default: local)"
    )
    
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=100,
        help="Number of predictions to simulate (default: 100)"
    )
    
    parser.add_argument(
        "--drift-demo",
        action="store_true",
        help="Simulate drift in second half of predictions"
    )
    
    parser.add_argument(
        "--export",
        default="predictions.csv",
        help="Export predictions to CSV file (local mode only, default: predictions.csv)"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "Performance Tracking Test Suite".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")
    print(Colors.RESET)
    
    if args.mode == "local":
        if not LOCAL_MODE_AVAILABLE:
            print_error("Local mode requires the performance module to be available")
            sys.exit(1)
        
        # Run local simulation
        predictions = simulate_predictions_local(args.count, args.drift_demo)
        
        time.sleep(1)
        show_metrics_local()
        
        if args.drift_demo:
            show_drift_indicators_local(window_size=args.count // 2)
        
        # Export
        export_predictions_local(args.export)
        
        print_success(f"Local simulation completed with {len(predictions)} predictions")
    
    elif args.mode == "api":
        # Run API tests
        test_api_endpoints(args.api_url, args.count, args.drift_demo)
        
        time.sleep(1)
        get_api_metrics(args.api_url)
        
        if args.drift_demo:
            get_api_drift(args.api_url, window_size=args.count // 2)
        
        print_success(f"API testing completed")
    
    print(f"\n{Colors.BOLD}Test completed!{Colors.RESET}\n")


if __name__ == "__main__":
    main()
