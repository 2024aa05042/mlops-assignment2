"""
Metrics collector script - collects metrics from running API and displays them.

Usage:
    python scripts/collect_metrics.py <API_URL> [--interval N] [--format json|table]

Examples:
    python scripts/collect_metrics.py http://localhost:8000
    python scripts/collect_metrics.py http://localhost:8000 --interval 5 --format table
    python scripts/collect_metrics.py http://localhost:8000 --format json > metrics.json
"""

import requests
import time
import sys
import argparse
import json
from typing import Dict, Any
from datetime import datetime
from pathlib import Path


def fetch_metrics(api_url: str) -> Dict[str, Any]:
    """Fetch metrics from the API."""
    try:
        response = requests.get(f"{api_url}/metrics", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metrics: {e}", file=sys.stderr)
        return None


def print_table_format(metrics: Dict[str, Any]) -> None:
    """Print metrics in a readable table format."""
    print("\n" + "=" * 80)
    print(f"API Metrics as of {metrics['timestamp']}")
    print("=" * 80 + "\n")
    
    # Overall stats
    print("OVERALL STATISTICS")
    print("-" * 80)
    print(f"  Total Requests:     {metrics['total_requests']}")
    print(f"  Total Errors:       {metrics['total_errors']}")
    print(f"  Error Rate:         {metrics['error_rate']:.2%}")
    
    # Latency stats
    print("\nLATENCY STATISTICS (milliseconds)")
    print("-" * 80)
    latency = metrics['latency_ms']
    print(f"  Average:            {latency['avg']:.2f} ms")
    print(f"  Min:                {latency['min']:.2f} ms")
    print(f"  Max:                {latency['max']:.2f} ms")
    print(f"  P50 (median):       {latency['p50']:.2f} ms")
    print(f"  P99 (99th percentile): {latency['p99']:.2f} ms")
    
    # By endpoint
    if metrics['by_endpoint']:
        print("\nBY ENDPOINT")
        print("-" * 80)
        for endpoint, stats in metrics['by_endpoint'].items():
            print(f"\n  {endpoint}")
            print(f"    Requests:       {stats['count']}")
            print(f"    Errors:         {stats['errors']}")
            print(f"    Avg Latency:    {stats['avg_latency_ms']:.2f} ms")
            print(f"    Min Latency:    {stats['min_latency_ms']:.2f} ms")
            print(f"    Max Latency:    {stats['max_latency_ms']:.2f} ms")
    
    # Status codes
    if metrics['by_status_code']:
        print("\nBY HTTP STATUS CODE")
        print("-" * 80)
        for code, count in sorted(metrics['by_status_code'].items(), key=lambda x: -x[1]):
            print(f"  {code}: {count}")
    
    # Predictions
    if metrics['predictions']:
        print("\nPREDICTION DISTRIBUTION")
        print("-" * 80)
        total_pred = sum(metrics['predictions'].values())
        for pred_class, count in sorted(metrics['predictions'].items(), key=lambda x: -x[1]):
            pct = (count / total_pred * 100) if total_pred > 0 else 0
            print(f"  {pred_class}: {count} ({pct:.1f}%)")
    
    print("\n" + "=" * 80 + "\n")


def print_json_format(metrics: Dict[str, Any]) -> None:
    """Print metrics in JSON format."""
    print(json.dumps(metrics, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Collect and display metrics from Cats vs Dogs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s http://localhost:8000
  %(prog)s http://localhost:8000 --interval 5 --format table
  %(prog)s http://localhost:8000 --format json > metrics.json
        """
    )
    
    parser.add_argument(
        "api_url",
        help="API URL (e.g., http://localhost:8000 or http://api.example.com)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Polling interval in seconds (0 = fetch once and exit, default: 0)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="table",
        help="Output format (default: table)",
    )
    
    args = parser.parse_args()
    
    try:
        if args.interval > 0:
            # Continuous polling
            print(f"Polling {args.api_url}/metrics every {args.interval} seconds (Ctrl+C to stop)")
            print()
            
            while True:
                metrics = fetch_metrics(args.api_url)
                if metrics:
                    if args.format == "json":
                        print_json_format(metrics)
                    else:
                        print_table_format(metrics)
                
                time.sleep(args.interval)
        
        else:
            # Single fetch
            metrics = fetch_metrics(args.api_url)
            if metrics:
                if args.format == "json":
                    print_json_format(metrics)
                else:
                    print_table_format(metrics)
            else:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n\nMetrics collection stopped.")


if __name__ == "__main__":
    main()
