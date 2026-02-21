#!/usr/bin/env python3

"""
Smoke Test Script for Cats vs Dogs API

Purpose: Verify API deployment by testing:
  1. Health endpoint responds correctly
  2. Prediction endpoint works with sample image
  3. API is ready to serve traffic

Usage:
  python smoke_test.py <API_URL> [--max-retries 30] [--retry-delay 2]

Examples:
  python smoke_test.py http://localhost:8000
  python smoke_test.py http://cats-dogs-api:8000 --max-retries 60
  python smoke_test.py http://10.0.0.5:8000 (minikube port-forward)

Exit Codes:
  0 = All tests passed
  1 = Health endpoint failed
  2 = Prediction endpoint failed
  3 = API unavailable after retries
  4 = Invalid arguments
  5 = Dependency error (missing requests/click)
"""

import sys
import time
import json
import argparse
from typing import Tuple, Optional
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("ERROR: requests library not found. Install with: pip install requests")
    sys.exit(5)


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    END = '\033[0m'


def print_header(text: str) -> None:
    """Print colored section header"""
    print(f"\n{Colors.BLUE}=== {text} ==={Colors.END}\n")


def print_success(text: str) -> None:
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print error message in red"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message in yellow"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message in blue"""
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")


def validate_arguments(api_url: str, max_retries: int, retry_delay: int) -> None:
    """Validate command-line arguments"""
    if not api_url:
        print_error("API_URL is required")
        sys.exit(4)

    if not api_url.startswith(('http://', 'https://')):
        print_error("API_URL must start with http:// or https://")
        sys.exit(4)

    if max_retries < 1 or not isinstance(max_retries, int):
        print_error("MAX_RETRIES must be a positive integer")
        sys.exit(4)

    if retry_delay < 1 or not isinstance(retry_delay, int):
        print_error("RETRY_DELAY must be a positive integer")
        sys.exit(4)

    print_info(f"API URL: {api_url}")
    print_info(f"Max retries: {max_retries} (every {retry_delay}s)")


def create_session() -> requests.Session:
    """Create requests session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def wait_for_api(
    session: requests.Session,
    api_url: str,
    max_retries: int,
    retry_delay: int,
    health_endpoint: str = "/health",
) -> bool:
    """Wait for API to become ready"""
    print_header("Step 1: Waiting for API to be ready")

    for attempt in range(max_retries):
        print_info(f"Attempt {attempt + 1}/{max_retries}: Checking API health...")

        try:
            response = session.get(
                f"{api_url}{health_endpoint}",
                timeout=5,
            )

            if response.status_code == 200:
                print_success(f"API is ready! (HTTP {response.status_code})")
                try:
                    print_info(f"Health response: {response.json()}")
                except json.JSONDecodeError:
                    print_info(f"Health response: {response.text}")
                return True

            print_warning(
                f"API not ready yet (HTTP {response.status_code}). "
                f"Retrying in {retry_delay}s..."
            )

        except requests.exceptions.RequestException as e:
            print_warning(
                f"Connection failed: {str(e)[:80]}... "
                f"Retrying in {retry_delay}s..."
            )

        time.sleep(retry_delay)

    print_error(f"API failed to become ready after {max_retries} attempts")
    return False


def test_health_endpoint(
    session: requests.Session,
    api_url: str,
    health_endpoint: str = "/health",
) -> bool:
    """Test health endpoint"""
    print_header("Step 2: Testing health endpoint")

    try:
        response = session.get(f"{api_url}{health_endpoint}", timeout=10)

        if response.status_code != 200:
            print_error(f"Health endpoint returned HTTP {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        try:
            data = response.json()
        except json.JSONDecodeError:
            print_error("Health endpoint did not return valid JSON")
            print_error(f"Response: {response.text}")
            return False

        print_success("Health endpoint working")
        print_info(f"Response: {json.dumps(data, indent=2)}")

        # Check for expected status field
        if data.get("status") == "healthy":
            print_success("API status is 'healthy'")

        return True

    except requests.exceptions.RequestException as e:
        print_error(f"Health endpoint test failed: {str(e)}")
        return False


def test_prediction_endpoint(
    session: requests.Session,
    api_url: str,
    test_image_path: str = "data/processed/train/cat/25.jpg",
    predict_endpoint: str = "/predict_path",
) -> bool:
    """Test prediction endpoint"""
    print_header("Step 3: Testing prediction endpoint")

    test_image = Path(test_image_path)
    if not test_image.exists():
        print_warning(f"Test image not found at {test_image_path}")
        print_warning("Continuing with prediction test anyway...")

    # Create prediction request
    payload = {"path": test_image_path}
    print_info(f"Sending prediction request with test image: {test_image_path}")

    try:
        response = session.post(
            f"{api_url}{predict_endpoint}",
            json=payload,
            timeout=10,
        )

        if response.status_code != 200:
            print_error(f"Prediction endpoint returned HTTP {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        try:
            data = response.json()
        except json.JSONDecodeError:
            print_error("Prediction endpoint did not return valid JSON")
            print_error(f"Response: {response.text}")
            return False

        print_success("Prediction endpoint working")
        print_info(f"Response: {json.dumps(data, indent=2)}")

        # Validate prediction results
        prediction_class = data.get("class")
        confidence = data.get("confidence")

        if prediction_class and confidence is not None:
            print_success(f"Prediction: Class={prediction_class}, Confidence={confidence}")

            # Validate class
            if prediction_class in ("cat", "dog"):
                print_success(f"Valid prediction class: {prediction_class}")
            else:
                print_warning(
                    f"Unexpected prediction class: {prediction_class} "
                    f"(expected 'cat' or 'dog')"
                )

            # Validate confidence
            if 0 <= confidence <= 1:
                print_success(f"Valid confidence score: {confidence}")
            else:
                print_warning(
                    f"Confidence score out of expected range: {confidence} "
                    f"(expected 0-1)"
                )
        else:
            print_warning("Could not extract prediction results from response")

        return True

    except requests.exceptions.RequestException as e:
        print_error(f"Prediction endpoint test failed: {str(e)}")
        return False


def print_summary(all_passed: bool) -> None:
    """Print test summary"""
    print_header("Smoke Test Summary")

    if all_passed:
        print_success("All smoke tests passed! ✓")
        print_info("API is ready to serve traffic")
    else:
        print_error("Smoke tests failed ✗")


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Smoke test script for Cats vs Dogs API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s http://localhost:8000
  %(prog)s http://cats-dogs-api:8000 --max-retries 60
  %(prog)s http://10.0.0.5:8000 --retry-delay 3
        """,
    )

    parser.add_argument(
        "api_url",
        help="API URL (e.g., http://localhost:8000)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=30,
        help="Maximum number of retries to wait for API (default: 30)",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=2,
        help="Delay between retries in seconds (default: 2)",
    )
    parser.add_argument(
        "--test-image",
        default="data/processed/train/cat/25.jpg",
        help="Path to test image (default: data/processed/train/cat/25.jpg)",
    )

    args = parser.parse_args()

    print_header("Cats vs Dogs API Smoke Tests")
    print_info("Starting smoke tests...")

    # Validate arguments
    validate_arguments(args.api_url, args.max_retries, args.retry_delay)

    # Create session
    session = create_session()

    # Run tests
    if not wait_for_api(session, args.api_url, args.max_retries, args.retry_delay):
        print_summary(False)
        sys.exit(3)

    if not test_health_endpoint(session, args.api_url):
        print_summary(False)
        sys.exit(1)

    if not test_prediction_endpoint(session, args.api_url, args.test_image):
        print_summary(False)
        sys.exit(2)

    # Success!
    print_summary(True)
    sys.exit(0)


if __name__ == "__main__":
    main()
