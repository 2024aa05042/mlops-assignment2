#!/bin/bash

################################################################################
# Smoke Test Script for Cats vs Dogs API
# 
# Purpose: Verify API deployment by testing:
#   1. Health endpoint responds correctly
#   2. Prediction endpoint works with sample image
#   3. API is ready to serve traffic
#
# Usage: ./smoke-test.sh <API_URL> [MAX_RETRIES] [RETRY_DELAY]
# 
# Examples:
#   ./smoke-test.sh http://localhost:8000
#   ./smoke-test.sh http://cats-dogs-api:8000 30 2
#   ./smoke-test.sh http://10.0.0.5:8000 (when port-forwarded from minikube)
#
# Exit Codes:
#   0 = All tests passed
#   1 = Health endpoint failed
#   2 = Prediction endpoint failed
#   3 = API unavailable after retries
#   4 = Invalid arguments
################################################################################

set -o pipefail

# Configuration
API_URL="${1:-http://localhost:8000}"
MAX_RETRIES="${2:-30}"
RETRY_DELAY="${3:-2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test data
TEST_IMAGE_PATH="data/processed/train/cat/25.jpg"
HEALTH_ENDPOINT="/health"
PREDICT_ENDPOINT="/predict_path"

################################################################################
# Utility Functions
################################################################################

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

################################################################################
# Validation Functions
################################################################################

validate_arguments() {
    if [[ -z "$API_URL" ]]; then
        print_error "API_URL is required"
        echo "Usage: $0 <API_URL> [MAX_RETRIES] [RETRY_DELAY]"
        exit 4
    fi

    # Validate URL format (basic check)
    if ! [[ "$API_URL" =~ ^https?:// ]]; then
        print_error "API_URL must start with http:// or https://"
        exit 4
    fi

    if ! [[ "$MAX_RETRIES" =~ ^[0-9]+$ ]] || [ "$MAX_RETRIES" -lt 1 ]; then
        print_error "MAX_RETRIES must be a positive integer"
        exit 4
    fi

    if ! [[ "$RETRY_DELAY" =~ ^[0-9]+$ ]] || [ "$RETRY_DELAY" -lt 1 ]; then
        print_error "RETRY_DELAY must be a positive integer"
        exit 4
    fi

    print_info "API URL: $API_URL"
    print_info "Max retries: $MAX_RETRIES (every ${RETRY_DELAY}s)"
}

################################################################################
# Health Check
################################################################################

wait_for_api() {
    print_header "Step 1: Waiting for API to be ready"
    
    local retry_count=0
    local max_attempts=$((MAX_RETRIES))

    while [ $retry_count -lt $max_attempts ]; do
        print_info "Attempt $((retry_count + 1))/$max_attempts: Checking API health..."
        
        # Try to reach the API
        local response=$(curl -s -w "\n%{http_code}" "$API_URL$HEALTH_ENDPOINT" 2>/dev/null)
        local http_code=$(echo "$response" | tail -n1)
        local body=$(echo "$response" | head -n-1)

        if [[ "$http_code" == "200" ]]; then
            print_success "API is ready! (HTTP $http_code)"
            print_info "Health response: $body"
            return 0
        fi

        print_warning "API not ready yet (HTTP $http_code). Retrying in ${RETRY_DELAY}s..."
        sleep "$RETRY_DELAY"
        ((retry_count++))
    done

    print_error "API failed to become ready after $max_attempts attempts"
    print_error "Last HTTP code: $http_code"
    return 3
}

################################################################################
# Health Endpoint Test
################################################################################

test_health_endpoint() {
    print_header "Step 2: Testing health endpoint"
    
    local response=$(curl -s -w "\n%{http_code}" "$API_URL$HEALTH_ENDPOINT" 2>/dev/null)
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)

    if [[ "$http_code" != "200" ]]; then
        print_error "Health endpoint returned HTTP $http_code"
        print_error "Response: $body"
        return 1
    fi

    # Verify response is valid JSON
    if ! echo "$body" | jq . >/dev/null 2>&1; then
        print_error "Health endpoint did not return valid JSON"
        print_error "Response: $body"
        return 1
    fi

    print_success "Health endpoint working"
    print_info "Response: $body"
    
    # Check for expected fields in health response
    local status=$(echo "$body" | jq -r '.status // empty' 2>/dev/null)
    if [[ "$status" == "healthy" ]]; then
        print_success "API status is 'healthy'"
    fi

    return 0
}

################################################################################
# Prediction Endpoint Test
################################################################################

test_prediction_endpoint() {
    print_header "Step 3: Testing prediction endpoint"
    
    if [[ ! -f "$TEST_IMAGE_PATH" ]]; then
        print_warning "Test image not found at $TEST_IMAGE_PATH"
        print_warning "Continuing with prediction test anyway..."
    fi

    # Create JSON payload with test image path
    local payload=$(cat <<EOF
{
    "path": "$TEST_IMAGE_PATH"
}
EOF
)

    print_info "Sending prediction request with test image: $TEST_IMAGE_PATH"
    
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_URL$PREDICT_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null)
    
    local http_code=$(echo "$response" | tail -n1)
    local body=$(echo "$response" | head -n-1)

    if [[ "$http_code" != "200" ]]; then
        print_error "Prediction endpoint returned HTTP $http_code"
        print_error "Response: $body"
        return 2
    fi

    # Verify response is valid JSON
    if ! echo "$body" | jq . >/dev/null 2>&1; then
        print_error "Prediction endpoint did not return valid JSON"
        print_error "Response: $body"
        return 2
    fi

    print_success "Prediction endpoint working"
    
    # Extract and display prediction results
    local class=$(echo "$body" | jq -r '.class // empty' 2>/dev/null)
    local confidence=$(echo "$body" | jq -r '.confidence // empty' 2>/dev/null)
    
    if [[ -n "$class" && -n "$confidence" ]]; then
        print_success "Prediction: Class=$class, Confidence=$confidence"
        
        # Basic validation: should be cat or dog
        if [[ "$class" =~ ^(cat|dog)$ ]]; then
            print_success "Valid prediction class: $class"
        else
            print_warning "Unexpected prediction class: $class (expected 'cat' or 'dog')"
        fi
        
        # Basic validation: confidence should be 0-1
        if (( $(echo "$confidence > 0 && $confidence <= 1" | bc -l 2>/dev/null || echo 0) )); then
            print_success "Valid confidence score: $confidence"
        else
            print_warning "Confidence score out of expected range: $confidence"
        fi
    else
        print_warning "Could not extract prediction results from response"
        print_info "Full response: $body"
    fi

    print_info "Response: $body"
    return 0
}

################################################################################
# Summary Report
################################################################################

print_summary() {
    print_header "Smoke Test Summary"
    
    if [[ $1 -eq 0 ]]; then
        print_success "All smoke tests passed! ✓"
        print_info "API is ready to serve traffic"
        return 0
    else
        print_error "Smoke tests failed ✗"
        return 1
    fi
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "Cats vs Dogs API Smoke Tests"
    print_info "Starting smoke tests..."
    
    # Validate input arguments
    validate_arguments
    
    # Wait for API to be ready
    if ! wait_for_api; then
        print_summary 1
        exit 3
    fi
    
    # Test health endpoint
    if ! test_health_endpoint; then
        print_summary 1
        exit 1
    fi
    
    # Test prediction endpoint
    if ! test_prediction_endpoint; then
        print_summary 1
        exit 2
    fi
    
    # Success!
    print_summary 0
    exit 0
}

# Execute main function
main
