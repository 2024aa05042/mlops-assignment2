# Post-Deployment Smoke Tests

## Overview

Smoke tests are automated tests that run **immediately after deployment** to verify that the API is functioning correctly. They test critical functionality and fail the pipeline if the deployment is broken.

**Key Features:**
- ✅ Automatically run after deployment in all CI/CD pipelines
- ✅ Fail the pipeline if tests fail (prevents broken deployments)
- ✅ Test health endpoint + prediction capability
- ✅ Available in bash and Python implementations
- ✅ Configurable retry logic for flaky infrastructure

---

## Smoke Test Scripts

### 1. Python Implementation (Recommended)

**File:** `tests/smoke_test.py`

**Features:**
- Comprehensive error handling
- Color-coded output
- JSON response validation
- Confidence score validation
- Prediction class validation
- Proper exit codes for CI/CD integration

**Usage:**
```bash
python smoke_test.py <API_URL> [--max-retries N] [--retry-delay N]
```

**Examples:**
```bash
# Test localhost
python smoke_test.py http://localhost:8000

# Test with custom retries
python smoke_test.py http://cats-dogs-api:8000 --max-retries 60 --retry-delay 2

# Test from port-forward
python smoke_test.py http://localhost:8001 --max-retries 30
```

**Exit Codes:**
| Code | Meaning |
|------|---------|
| 0 | All tests passed ✅ |
| 1 | Health endpoint failed ❌ |
| 2 | Prediction endpoint failed ❌ |
| 3 | API unavailable after retries ❌ |
| 4 | Invalid arguments ❌ |
| 5 | Missing dependencies (requests) ❌ |

**Output Example:**
```
=== Cats vs Dogs API Smoke Tests ===

ℹ API URL: http://localhost:8000
ℹ Max retries: 30 (every 2s)

=== Step 1: Waiting for API to be ready ===

ℹ Attempt 1/30: Checking API health...
ℹ Attempt 2/30: Checking API health...
✓ API is ready! (HTTP 200)
ℹ Health response: {'status': 'healthy', 'timestamp': '2026-02-21T10:30:45'}

=== Step 2: Testing health endpoint ===

✓ Health endpoint working
ℹ Response: {'status': 'healthy', ...}
✓ API status is 'healthy'

=== Step 3: Testing prediction endpoint ===

ℹ Sending prediction request with test image: data/processed/train/cat/25.jpg
✓ Prediction endpoint working
✓ Prediction: Class=cat, Confidence=0.983
✓ Valid prediction class: cat
✓ Valid confidence score: 0.983

=== Smoke Test Summary ===

✓ All smoke tests passed! ✓
ℹ API is ready to serve traffic
```

### 2. Bash Implementation

**File:** `scripts/smoke-test.sh`

**Features:**
- No Python dependency required
- Cross-platform compatible
- Same comprehensive error handling as Python
- Useful for debugging and manual testing

**Usage:**
```bash
./smoke-test.sh <API_URL> [MAX_RETRIES] [RETRY_DELAY]
```

**Examples:**
```bash
# Test localhost
./smoke-test.sh http://localhost:8000

# Test with custom retries
./smoke-test.sh http://cats-dogs-api:8000 30 2

# Quick test (fewer retries)
./smoke-test.sh http://localhost:8000 5 1
```

---

## Integration with CI/CD Pipelines

### GitHub Actions

**File:** `.github/workflows/ci.yml`

Smoke tests run automatically in the `deploy` job after successfully deploying to Kubernetes:

```yaml
- name: Run smoke tests (health + prediction)
  if: ${{ secrets.KUBECONFIG }}
  timeout-minutes: 10
  run: |
    # Port forward and run Python smoke tests
    kubectl port-forward -n default svc/cats-dogs-api 8001:8000 &
    pip install requests
    python tests/smoke_test.py http://localhost:8001 --max-retries 30 --retry-delay 1
```

**When it runs:**
- ✅ On every push to main branch (after deployment)
- ✅ Automatically fails pipeline if tests fail
- ✅ Timeout: 10 minutes

### Argo CD Workflow

**File:** `.github/workflows/cd-argocd.yml`

Enhanced with comprehensive smoke tests in `deploy-argocd` job:

```yaml
- name: Run smoke tests (health + prediction)
  if: ${{ secrets.KUBECONFIG }}
  timeout-minutes: 10
  run: |
    kubectl port-forward -n default svc/cats-dogs-api 8001:8000 &
    pip install requests
    python tests/smoke_test.py http://localhost:8001 --max-retries 30 --retry-delay 1
```

### Deploy Script

**File:** `scripts/deploy.sh`

Integrated into deployment workflow:

```bash
# Run deployment
./scripts/deploy.sh local latest

# Smoke tests run automatically after deployment
# If tests fail, script exits with error code 1
```

**Behavior:**
- Automatically port-forwards to the service
- Runs Python or bash smoke tests (whichever available)
- Fails deployment if tests fail
- Cleans up port forwarding afterwards

**Usage:**
```bash
# Deploy with automatic smoke tests
./scripts/deploy.sh staging latest

# Deploy to production (with smoke tests)
./scripts/deploy.sh prod v1.2.3
```

### Jenkins Pipeline

**File:** `Jenkinsfile`

Enhanced `Smoke Tests` stage runs after each deployment:

```groovy
stage('Smoke Tests') {
    when {
        expression { return params.DEPLOY }
    }
    steps {
        sh '''
            pip install requests
            kubectl port-forward -n production svc/cats-dogs-api 8001:8000 &
            python3 tests/smoke_test.py http://localhost:8001 \
                --max-retries 30 --retry-delay 1 \
                --test-image data/processed/train/cat/25.jpg
        '''
    }
}
```

**Features:**
- Runs after successful deployment to production/staging/dev
- Validates environment-specific endpoints
- Email notifications on success/failure

---

## What Gets Tested

### 1. Health Endpoint (`GET /health`)

Tests that the API is running and ready to serve requests.

**Checks:**
- ✅ Returns HTTP 200
- ✅ Valid JSON response
- ✅ Status field is "healthy"

**Sample Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-21T10:30:45.123Z",
  "version": "1.0.0"
}
```

### 2. Prediction Endpoint (`POST /predict_path`)

Tests that the model can make predictions on sample images.

**Input:**
```json
{
  "path": "data/processed/train/cat/25.jpg"
}
```

**Checks:**
- ✅ Returns HTTP 200
- ✅ Valid JSON response
- ✅ Prediction class is either "cat" or "dog"
- ✅ Confidence score is between 0 and 1
- ✅ Response contains class and confidence fields

**Sample Response:**
```json
{
  "class": "cat",
  "confidence": 0.9832,
  "model_version": "v1.0",
  "inference_time_ms": 124
}
```

### 3. API Readiness

Tests that the API takes ~30 seconds to start (configurable).

**Retry Logic:**
- Max 30 retries (configurable)
- 2-second delay between retries (configurable)
- Total: ~60 seconds to wait for API startup

---

## Running Smoke Tests Manually

### Before Deployment

```bash
# Start the API locally
docker run -p 8000:8000 cats-dogs-api:latest

# In another terminal
python tests/smoke_test.py http://localhost:8000
```

### After Kubernetes Deployment

```bash
# Port forward to the service
kubectl port-forward svc/cats-dogs-api 8001:8000

# In another terminal
python tests/smoke_test.py http://localhost:8001
```

### With Custom Test Image

```bash
python tests/smoke_test.py http://localhost:8000 --test-image data/processed/train/dog/1000.jpg
```

---

## Troubleshooting Smoke Tests

### Issue: "API failed to become ready after X attempts"

**Cause:** API took too long to start or is not responding

**Solutions:**
```bash
# Check pod logs
kubectl logs -l app=cats-dogs-api -f

# Check pod status
kubectl get pods -l app=cats-dogs-api

# Increase max retries
python tests/smoke_test.py http://localhost:8001 --max-retries 60 --retry-delay 2

# Check if API is listening
kubectl exec -it <pod-name> -- curl http://localhost:8000/health
```

### Issue: "Health endpoint returned HTTP 500"

**Cause:** API crashed or has initialization error

**Solutions:**
```bash
# Check full pod logs
kubectl logs -l app=cats-dogs-api -f --tail=100

# Check pod events
kubectl describe pod -l app=cats-dogs-api

# Verify environment variables
kubectl exec -it <pod-name> -- env | grep -i model
```

### Issue: "Prediction endpoint did not return valid JSON"

**Cause:** API returned error or unexpected format

**Solutions:**
```bash
# Test directly with curl
curl -X POST http://localhost:8001/predict_path \
  -H "Content-Type: application/json" \
  -d '{"path":"data/processed/train/cat/25.jpg"}'

# Check API logs
kubectl logs -l app=cats-dogs-api | grep -i error

# Verify test image exists
kubectl exec -it <pod-name> -- ls -la data/processed/train/cat/25.jpg
```

### Issue: "Prediction: Class=unknown, Confidence=0.0"

**Cause:** Model inference failed due to:
- Corrupted weights file
- Incompatible PyTorch version
- Image processing issue

**Solutions:**
```bash
# Verify model file exists in container
kubectl exec -it <pod-name> -- ls -la models/

# Check model loading in application logs
kubectl logs -l app=cats-dogs-api | grep -i "loading model"

# Verify image file is accessible
kubectl exec -it <pod-name> -- file data/processed/train/cat/25.jpg

# Test model directly in pod
kubectl exec -it <pod-name> -- python -c \
  "from src.api import model; print(model)"
```

### Issue: "Connection failed" / "Port forwarding not working"

**Cause:** Network or port forwarding issue

**Solutions:**
```bash
# Check service exists
kubectl get svc cats-dogs-api

# Check service endpoints
kubectl get endpoints cats-dogs-api

# Try direct pod port-forward
POD=$(kubectl get po -l app=cats-dogs-api -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward po/$POD 8001:8000

# Or use specific service port
kubectl port-forward svc/cats-dogs-api 8001:8000 -v=4  # Verbose mode for debugging
```

---

## Customizing Smoke Tests

### Adding Custom Checks

Edit `tests/smoke_test.py`:

```python
# Add a new test function
def test_model_accuracy():
    """Test that model accuracy meets threshold"""
    # Run 100 test images and check accuracy >= 85%
    pass

# Add to main()
if not test_model_accuracy():
    sys.exit(1)
```

### Changing Test Image

```bash
# Use different test image
python tests/smoke_test.py http://localhost:8000 \
  --test-image data/processed/train/dog/2000.jpg
```

### Increasing Retry Timeout

```bash
# Wait up to 3 minutes (60 retries × 3s delay)
python tests/smoke_test.py http://localhost:8000 \
  --max-retries 60 \
  --retry-delay 3
```

---

## Performance Baselines

Expected API response times:

| Endpoint | Typical | Max |
|----------|---------|-----|
| `/health` | 5ms | 100ms |
| `/predict_path` | 100-200ms | 500ms |
| First prediction (cold start) | 500-1000ms | 2000ms |

If smoke tests are significantly slower, check:
- Container resource limits
- Kubernetes node CPU/memory availability
- Model inference latency

---

## CI/CD Integration Checklist

Before merging smoke tests to production:

- [ ] All smoke tests pass locally with `docker run`
- [ ] All smoke tests pass against minikube deployment
- [ ] All smoke tests pass against staging cluster
- [ ] Exit codes are correct (0 on success, non-0 on failure)
- [ ] Port forwarding cleanup is working properly
- [ ] Retry logic handles transient failures gracefully
- [ ] Error messages are descriptive
- [ ] Documentation is up-to-date
- [ ] GitHub Actions workflow has timeout limits
- [ ] Jenkins pipeline uses proper namespace detection

---

## Summary

**What was added:**
- ✅ Python smoke test script with comprehensive validation
- ✅ Bash smoke test script for cross-platform compatibility
- ✅ Integration into GitHub Actions CI/CD
- ✅ Integration into Argo CD workflow
- ✅ Integration into universal deploy script
- ✅ Enhanced Jenkinsfile with robust smoke tests
- ✅ Automatic pipeline failure if tests fail

**Result:** Deployments now automatically validate that the API is working before marking them as successful. This prevents broken deployments from reaching production.
