# Smoke Tests Quick Reference

## 📋 Files Created

| File | Size | Purpose |
|------|------|---------|
| `tests/smoke_test.py` | 380 lines | Python smoke tests (recommended) |
| `scripts/smoke-test.sh` | 240 lines | Bash smoke tests (cross-platform) |
| `SMOKE_TESTS_GUIDE.md` | 450+ lines | Comprehensive guide |
| `SMOKE_TESTS_IMPLEMENTATION.md` | 350+ lines | Implementation summary |

## 🚀 Quick Start

### Test Locally

```bash
# Start API in Docker
docker run -p 8000:8000 cats-dogs-api:latest

# In another terminal
python tests/smoke_test.py http://localhost:8000
```

### Test in Kubernetes

```bash
# Port forward
kubectl port-forward svc/cats-dogs-api 8001:8000

# In another terminal
python tests/smoke_test.py http://localhost:8001
```

### Deploy with Automatic Tests

```bash
# Tests run automatically after deployment
./scripts/deploy.sh production v1.2.3

# If tests fail, deployment fails (exit code 1)
```

## ✅ What Gets Tested

1. **Health Endpoint** (`GET /health`)
   - API responds with 200 OK
   - Returns valid JSON
   - Status is "healthy"

2. **Prediction Endpoint** (`POST /predict_path`)
   - API makes predictions correctly
   - Returns class (cat/dog) and confidence
   - Confidence is between 0-1

3. **API Readiness**
   - Waits gracefully for API startup
   - Retries automatically on transient failures

## 📊 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | ✅ All tests passed |
| 1 | ❌ Health endpoint failed |
| 2 | ❌ Prediction endpoint failed |
| 3 | ❌ API unavailable (timeout) |
| 4 | ❌ Invalid arguments |
| 5 | ❌ Missing dependencies |

## 🔧 CI/CD Integration

### GitHub Actions (`.github/workflows/ci.yml`)
- ✅ Runs after deployment on `main`
- ✅ Fails workflow if tests fail
- ✅ Timeout: 10 minutes

### Argo CD (`.github/workflows/cd-argocd.yml`)
- ✅ Runs after Argo CD sync on `main`
- ✅ Fails workflow if tests fail
- ✅ Timeout: 10 minutes

### Deploy Script (`scripts/deploy.sh`)
- ✅ Automatic after deployment
- ✅ Fails with exit code 1 if tests fail
- ✅ All environments (local/staging/prod)

### Jenkins (`Jenkinsfile`)
- ✅ Runs after each environment deployment
- ✅ Fails build if tests fail
- ✅ Namespace auto-detected from branch

## 💡 Key Features

✅ **Automatic Pipeline Failure** - Broken deployments are caught immediately
✅ **Configurable Retries** - Handle slow infrastructure gracefully
✅ **Multiple Implementations** - Python (recommended) and Bash
✅ **Color Output** - Easy to read results
✅ **Proper Exit Codes** - CI/CD friendly
✅ **Timeout Handling** - Won't hang forever
✅ **Port Forwarding** - Works with Kubernetes services
✅ **JSON Validation** - Checks response format

## 🔍 Troubleshooting

**"API failed to become ready"**
```bash
# Increase retries
python tests/smoke_test.py http://localhost:8001 --max-retries 60 --retry-delay 2

# Check logs
kubectl logs -l app=cats-dogs-api -f
```

**"Health endpoint returned HTTP 500"**
```bash
# Check pod status
kubectl describe pod -l app=cats-dogs-api

# View recent logs
kubectl logs -l app=cats-dogs-api --tail=50
```

**"Prediction failed"**
```bash
# Test directly
curl -X POST http://localhost:8001/predict_path \
  -H "Content-Type: application/json" \
  -d '{"path":"data/processed/train/cat/25.jpg"}'

# Check model file
kubectl exec <pod-name> -- ls models/
```

## 📖 Documentation

- **[SMOKE_TESTS_GUIDE.md](SMOKE_TESTS_GUIDE.md)** - Full guide with examples, troubleshooting, customization
- **[SMOKE_TESTS_IMPLEMENTATION.md](SMOKE_TESTS_IMPLEMENTATION.md)** - Implementation details, metrics, success criteria

## 🎯 Usage Examples

### Python Script (Recommended)

```bash
# Basic usage
python tests/smoke_test.py http://localhost:8000

# With custom retries
python tests/smoke_test.py http://localhost:8001 \
  --max-retries 60 \
  --retry-delay 2

# With different test image
python tests/smoke_test.py http://localhost:8000 \
  --test-image data/processed/train/dog/1000.jpg
```

### Bash Script

```bash
# Basic usage
./smoke-test.sh http://localhost:8000

# With custom retries
./smoke-test.sh http://localhost:8000 60 2

# Shorter timeout (5 retries, 1s each)
./smoke-test.sh http://localhost:8000 5 1
```

### From Pipeline

```bash
# GitHub Actions
python tests/smoke_test.py http://localhost:8001 --max-retries 30 --retry-delay 1

# Jenkins
python3 tests/smoke_test.py http://localhost:8001 --max-retries 30

# Deploy script
./scripts/deploy.sh production v1.2.3  # Tests run automatically
```

## 💻 Dependencies

### Python Script
- `requests` (automatically installed in pipelines)
- `python3`
- `curl` (for port forwarding)
- `kubectl` (for port forwarding)

### Bash Script
- `bash`
- `curl`
- `jq` (for JSON parsing)
- `kubectl` (for port forwarding)

## ⚡ Performance

Typical execution times:

| Scenario | Time |
|----------|------|
| Health endpoint | 5-50ms |
| Prediction endpoint | 100-200ms |
| Full smoke test (both endpoints) | 200-300ms |
| With API startup wait | 30-60 seconds |
| With custom retries (60x) | 2-3 minutes |

---

## 📝 Summary

Smoke tests are now **automatically run after every deployment** in all CI/CD pipelines:

✅ **GitHub Actions** - Fails workflow if tests fail
✅ **Argo CD** - Fails deployment if tests fail
✅ **Deploy Script** - Fails with error if tests fail
✅ **Jenkins** - Fails build if tests fail

**Result:** Broken deployments are caught immediately, preventing broken services from reaching production.

See [SMOKE_TESTS_GUIDE.md](SMOKE_TESTS_GUIDE.md) for complete documentation.
