# Monitoring & Logging Guide

## Overview

The Cats vs Dogs API includes comprehensive request/response logging and metrics collection to track API health, performance, and usage patterns.

**Key Features:**
- ✅ Structured request/response logging
- ✅ Request latency tracking with percentiles (P50, P99)
- ✅ HTTP status code distribution
- ✅ Per-endpoint statistics
- ✅ Prediction class distribution
- ✅ Error tracking and rates
- ✅ Sensitive data exclusion
- ✅ Multiple output formats (JSON, table)
- ✅ Real-time metrics endpoint

---

## Architecture

### Components

1. **`src/monitoring.py`** - Core monitoring module
   - `setup_logging()` - Initialize structured logging
   - `LoggingMiddleware` - ASGI middleware for request/response logging
   - `MetricsCollector` - In-memory metrics storage
   - Helper functions for logging predictions

2. **`src/api.py`** - Enhanced API with logging
   - Initialized logging on startup
   - Added metrics endpoint (`GET /metrics`)
   - Added metrics reset endpoint (`POST /metrics/reset`)
   - All endpoints log requests and predictions

3. **`scripts/collect_metrics.py`** - Metrics collection tool
   - Fetch metrics from running API
   - Display in table or JSON format
   - Continuous polling with configurable interval

4. **`logging.yaml`** - Logging configuration
   - Structured log format
   - Rotating file handlers
   - Separate error logs
   - Environment-specific settings

---

## Logging

### Request/Response Logging

Every request is automatically logged by the `LoggingMiddleware`:

```
2026-02-21 10:30:45 - cats-dogs-api - INFO - Incoming request
2026-02-21 10:30:45 - cats-dogs-api - INFO - Response sent
```

**Logged Information:**
- Request method (GET, POST, etc.)
- Request path (/health, /predict, /predict_path)
- Query parameters (excluded: sensitive data)
- HTTP status code
- Response latency in milliseconds
- Request ID (from x-request-id header if present)

**Excluded Sensitive Data:**
- Request/response bodies (except status)
- File contents
- Credentials and tokens
- Authentication headers (Authorization, X-API-Key, etc.)
- Cookies
- Passwords and API keys

### Prediction Logging

Predictions are logged with structured format:

```
2026-02-21 10:30:46 - cats-dogs-api - INFO - Prediction made
   - request_id: abc123
   - endpoint: /predict_path
   - prediction_class: cat
   - confidence: 0.9832
```

### Error Logging

Errors include stack traces for debugging:

```
2026-02-21 10:30:47 - cats-dogs-api - ERROR - Failed to read image: 
   - request_id: xyz789
   - path: data/processed/train/nonexistent.jpg
   - error: File not found
   (full stack trace included)
```

### Log Levels

Control logging verbosity via `LOG_LEVEL` environment variable:

```bash
# INFO level (default)
docker run -e LOG_LEVEL=INFO cats-dogs-api

# DEBUG level (very verbose)
docker run -e LOG_LEVEL=DEBUG cats-dogs-api

# WARNING level (less verbose)
docker run -e LOG_LEVEL=WARNING cats-dogs-api
```

**Levels:**
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational messages (default)
- `WARNING` - Warning messages
- `ERROR` - Error messages
- `CRITICAL` - Critical errors

---

## Metrics

### Metrics Endpoint

Get real-time API metrics in JSON format:

```bash
curl http://localhost:8000/metrics
```

**Response Example:**
```json
{
  "timestamp": "2026-02-21T10:30:45.123Z",
  "total_requests": 1523,
  "total_errors": 8,
  "error_rate": 0.0053,
  "latency_ms": {
    "avg": 142.56,
    "p50": 125.30,
    "p99": 450.20,
    "min": 5.10,
    "max": 2134.50
  },
  "by_endpoint": {
    "/predict": {
      "count": 800,
      "errors": 2,
      "avg_latency_ms": 156.20,
      "min_latency_ms": 120.00,
      "max_latency_ms": 2134.50
    },
    "/predict_path": {
      "count": 700,
      "errors": 5,
      "avg_latency_ms": 128.30,
      "min_latency_ms": 90.00,
      "max_latency_ms": 1200.00
    },
    "/health": {
      "count": 23,
      "errors": 1,
      "avg_latency_ms": 8.50,
      "min_latency_ms": 5.00,
      "max_latency_ms": 25.00
    }
  },
  "by_status_code": {
    "200": 1515,
    "400": 5,
    "500": 3
  },
  "predictions": {
    "cat": 780,
    "dog": 715
  }
}
```

### Tracked Metrics

**Global Metrics:**
- `total_requests` - Total requests received
- `total_errors` - Total requests with errors
- `error_rate` - Percentage of requests that errored

**Latency Metrics (milliseconds):**
- `avg` - Average response time
- `p50` - Median (50th percentile)
- `p99` - 99th percentile (few requests slower than this)
- `min` - Fastest response
- `max` - Slowest response

**Per-Endpoint Breakdown:**
- `count` - Number of requests
- `errors` - Number of errors
- `avg_latency_ms` - Average latency
- `min_latency_ms` - Fastest response
- `max_latency_ms` - Slowest response

**HTTP Status Codes:**
- `200` - Successful predictions
- `400` - Bad request (invalid image, missing file)
- `500` - Server error (model load failure)

**Prediction Distribution:**
- `cat` - Count of cat predictions
- `dog` - Count of dog predictions

---

## Metrics Collection

### Using the Collection Script

Display metrics in real-time:

```bash
# Fetch metrics once and display in table format
python scripts/collect_metrics.py http://localhost:8000

# Display in JSON format
python scripts/collect_metrics.py http://localhost:8000 --format json

# Poll every 5 seconds
python scripts/collect_metrics.py http://localhost:8000 --interval 5

# Save to file
python scripts/collect_metrics.py http://localhost:8000 --format json > metrics.json
```

### Table Output Example

```
================================================================================
API Metrics as of 2026-02-21T10:30:45.123Z
================================================================================

OVERALL STATISTICS
--------------------------------------------------------------------------------
  Total Requests:     1523
  Total Errors:       8
  Error Rate:        0.53%

LATENCY STATISTICS (milliseconds)
--------------------------------------------------------------------------------
  Average:            142.56 ms
  Min:                5.10 ms
  Max:                2134.50 ms
  P50 (median):       125.30 ms
  P99 (99th percentile): 450.20 ms

BY ENDPOINT
--------------------------------------------------------------------------------

  /predict
    Requests:       800
    Errors:         2
    Avg Latency:    156.20 ms
    Min Latency:    120.00 ms
    Max Latency:    2134.50 ms

  /predict_path
    Requests:       700
    Errors:         5
    Avg Latency:    128.30 ms
    Min Latency:    90.00 ms
    Max Latency:    1200.00 ms

BY HTTP STATUS CODE
--------------------------------------------------------------------------------
  200: 1515
  400: 5
  500: 3

PREDICTION DISTRIBUTION
--------------------------------------------------------------------------------
  cat: 780 (52.3%)
  dog: 715 (47.7%)

================================================================================
```

### Resetting Metrics

Reset all collected metrics:

```bash
curl -X POST http://localhost:8000/metrics/reset
```

Response:
```json
{"status": "Metrics reset successfully"}
```

---

## Local Development

### Running with Logging

**Using Docker:**
```bash
docker run \
  -e LOG_LEVEL=DEBUG \
  -p 8000:8000 \
  -v "${PWD}/data:/app/data" \
  cats-dogs-api:latest
```

**Using Python directly:**
```bash
# Set environment variable
export LOG_LEVEL=INFO

# Run API
python -m uvicorn src.api:app --host 0.0.0.0 --port 8000 --log-level info
```

### Testing Logging

Make predictions and check logs:

```bash
# In one terminal, run the API
docker run -p 8000:8000 -v "${PWD}/data:/app/data" cats-dogs-api

# In another terminal, make a prediction
curl -X POST http://localhost:8000/predict_path \
  -H "Content-Type: application/json" \
  -d '{"path":"data/processed/train/cat/25.jpg"}'

# Check metrics
python scripts/collect_metrics.py http://localhost:8000 --format table
```

---

## Kubernetes Deployment

### View Logs

**Current pod:**
```bash
kubectl logs -l app=cats-dogs-api --follow
```

**Specific pod:**
```bash
kubectl logs <pod-name>
```

**Last 100 lines:**
```bash
kubectl logs -l app=cats-dogs-api --tail=100
```

**Since specific time:**
```bash
kubectl logs -l app=cats-dogs-api --since=10m
```

### Collect Metrics from K8s

**Direct pod access:**
```bash
# Port forward
kubectl port-forward svc/cats-dogs-api 8001:8000

# In another terminal
python scripts/collect_metrics.py http://localhost:8001
```

**From within cluster:**
```bash
# Access from another pod
kubectl exec -it <pod> -- curl http://cats-dogs-api:8000/metrics
```

### Environment Variables

Set in deployment:

```yaml
env:
  - name: LOG_LEVEL
    value: "INFO"
  - name: PYTHONUNBUFFERED
    value: "1"
```

---

## Production Considerations

### Log Storage

In Kubernetes, logs are stored in container `stdout`/`stderr`. For production:

1. **Logging Agent (recommended):**
   - Use Fluentd, Logstash, or Filebeat
   - Ship logs to centralized system (ELK stack, Splunk, etc.)

2. **Configuration:**
   ```yaml
   # kubernetes/deployment.yaml
   spec:
     containers:
       - name: api
         image: cats-dogs-api:latest
         env:
           - name: LOG_LEVEL
             value: "INFO"
   ```

3. **Log Rotation:**
   - Docker/Kubernetes handle rotation automatically
   - Configure in logging.yaml for file handlers

### Metrics Collection in Production

1. **Kubernetes-native:**
   ```bash
   # From your monitoring system
   kubectl port-forward svc/cats-dogs-api 8001:8000
   curl http://localhost:8001/metrics
   ```

2. **Custom scraper:**
   ```bash
   while true; do
     curl -s http://api-service:8000/metrics | jq .
     sleep 60
   done
   ```

3. **Prometheus integration (future):**
   - Export metrics endpoint in Prometheus format
   - Kubernetes scrapes automatically via ServiceMonitor

### Sensitive Data Security

✅ **Already excluded:**
- Request/response bodies (status only)
- Authentication headers
- Credentials and tokens
- Cookies and sessions
- Passwords and API keys

⚠️ **Be careful with:**
- File paths in logs (don't log full paths in production)
- User input (sanitized before logging)
- Personal information (if processing)

---

## Monitoring Dashboard

### Real-time Dashboard

```bash
# Watch metrics every 5 seconds
watch -n 5 'python scripts/collect_metrics.py http://localhost:8000 --format table'
```

### Example Monitoring Script

Save as `monitor.sh`:

```bash
#!/bin/bash
API_URL="http://localhost:8000"
INTERVAL=10

while true; do
  clear
  echo "Monitoring Cats vs Dogs API: $API_URL"
  echo "Updated: $(date)"
  echo ""
  
  python scripts/collect_metrics.py "$API_URL" --format table
  
  sleep $INTERVAL
done
```

Run it:
```bash
chmod +x monitor.sh
./monitor.sh
```

---

## Troubleshooting

### Issue: No logs appearing

**Solution:**
```bash
# Check LOG_LEVEL environment variable
docker exec <container> env | grep LOG_LEVEL

# If not set, set it
docker exec <container> export LOG_LEVEL=INFO
```

### Issue: Metrics endpoint returns empty

**Solution:**
```bash
# Check if any requests have been made
curl http://localhost:8000/metrics | jq '.total_requests'

# Make a test request
curl http://localhost:8000/health

# Check metrics again
curl http://localhost:8000/metrics
```

### Issue: High latency in metrics

**Solution:**
```bash
# Check which endpoint is slow
curl http://localhost:8000/metrics | jq '.by_endpoint'

# Check system resources
kubectl describe node
kubectl top node

# Check pod resources
kubectl top pod -l app=cats-dogs-api
```

### Issue: Error rate too high

**Solution:**
```bash
# Check error distribution
curl http://localhost:8000/metrics | jq '.by_status_code'

# Check API logs for errors
kubectl logs -l app=cats-dogs-api | grep ERROR
```

---

## Summary

The monitoring and logging system provides:

✅ **Structured Request Logging** - Every request logged with context
✅ **Metric Collection** - Per-endpoint stats with latency percentiles
✅ **Real-time Metrics API** - JSON endpoint for integration
✅ **Sensitive Data Protection** - Automatic exclusion of sensitive data
✅ **Error Tracking** - Detailed error logs with stack traces
✅ **Prediction Audit Trail** - Log of all predictions made
✅ **Collection Tools** - Scripts for gathering and displaying metrics
✅ **Production Ready** - Log rotation, environment config, scaling-ready

**Quick Start:**
```bash
# Run API with logging
docker run -e LOG_LEVEL=INFO -p 8000:8000 cats-dogs-api

# View metrics
python scripts/collect_metrics.py http://localhost:8000

# Watch real-time
python scripts/collect_metrics.py http://localhost:8000 --interval 5
```
