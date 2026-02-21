# Monitoring & Logging Quick Reference

## 📊 Key Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```
Response: `{"status": "healthy", "timestamp": 1645345445.123, "service": "cats-dogs-api"}`

### View Metrics
```bash
curl http://localhost:8000/metrics | jq
```

### Reset Metrics
```bash
curl -X POST http://localhost:8000/metrics/reset
```

---

## 📈 Metrics Explained

| Metric | Meaning | Example |
|--------|---------|---------|
| `total_requests` | Total API calls | 1523 |
| `total_errors` | Failed requests | 8 |
| `error_rate` | % of failed requests | 0.53% |
| `avg_latency_ms` | Average response time | 142.56 ms |
| `p99_latency_ms` | 99% of requests faster | 450.20 ms |
| `by_endpoint` | Per-endpoint statistics | `/predict`: 800 requests |
| `predictions` | Count by class | cat: 780, dog: 715 |
| `by_status_code` | HTTP codes | 200: 1515, 400: 5 |

---

## 🔍 Using Collection Script

**Table format (readable):**
```bash
python scripts/collect_metrics.py http://localhost:8000 --format table
```

**JSON format (machine-readable):**
```bash
python scripts/collect_metrics.py http://localhost:8000 --format json
```

**Continuous monitoring (every 5 seconds):**
```bash
python scripts/collect_metrics.py http://localhost:8000 --interval 5
```

**Save to file:**
```bash
python scripts/collect_metrics.py http://localhost:8000 --format json > metrics.json
```

---

## 📝 Log Levels

Set via `LOG_LEVEL` environment variable:

```bash
# DEBUG - verbose (dev only)
docker run -e LOG_LEVEL=DEBUG cats-dogs-api

# INFO - normal (production)
docker run -e LOG_LEVEL=INFO cats-dogs-api

# WARNING - quiet (errors only)
docker run -e LOG_LEVEL=WARNING cats-dogs-api
```

---

## 📋 What Gets Logged

✅ **Every Request:**
- Method, path, query params
- HTTP status code
- Response latency
- Request ID (if provided)

✅ **Every Prediction:**
- Prediction class (cat/dog)
- Confidence score
- Endpoint used

✅ **All Errors:**
- Full stack trace
- Error message
- Context information

❌ **Never Logged (sensitive data):**
- Request bodies
- Response bodies
- Authentication headers
- Credentials
- File contents

---

## 🐳 Docker

**Run with logging:**
```bash
docker run \
  -e LOG_LEVEL=INFO \
  -p 8000:8000 \
  -v "${PWD}/data:/app/data" \
  cats-dogs-api:latest
```

**Check logs:**
```bash
docker logs <container-id>
docker logs <container-id> -f  # follow
```

---

## ☸️ Kubernetes

**View logs:**
```bash
kubectl logs -l app=cats-dogs-api          # current
kubectl logs -l app=cats-dogs-api -f       # follow
kubectl logs -l app=cats-dogs-api --tail=100  # last 100 lines
```

**Collect metrics:**
```bash
# From outside cluster
kubectl port-forward svc/cats-dogs-api 8001:8000
python scripts/collect_metrics.py http://localhost:8001

# From inside cluster
kubectl exec -it <pod> -- curl http://localhost:8000/metrics
```

**Check pod resources:**
```bash
kubectl top pod -l app=cats-dogs-api
```

---

## 🎯 Common Tasks

### Monitor API in real-time
```bash
watch -n 5 'curl -s http://localhost:8000/metrics | jq ".latency_ms, .total_requests"'
```

### Check error rate
```bash
curl -s http://localhost:8000/metrics | jq '.error_rate'
```

### See top predictions
```bash
curl -s http://localhost:8000/metrics | jq '.predictions | sort_by(.) | reverse'
```

### View latency percentiles
```bash
curl -s http://localhost:8000/metrics | jq '.latency_ms'
```

### Check endpoint performance
```bash
curl -s http://localhost:8000/metrics | jq '.by_endpoint | to_entries[] | {endpoint: .key, avg_latency: .value.avg_latency_ms, errors: .value.errors}'
```

---

## 📊 Performance Baselines

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| Avg Latency | < 200ms | 200-500ms | > 500ms |
| P99 Latency | < 1000ms | 1-2s | > 2s |
| Error Rate | < 1% | 1-5% | > 5% |
| Request Count | Any | > 1000/min | > 10000/min |

---

## 🚨 Alert Thresholds

Monitor and alert when:
- `error_rate > 0.05` (5% errors)
- `avg_latency_ms > 500` (slow responses)
- `total_errors > 10` in 5 minutes
- `p99_latency_ms > 2000` (tail latency spike)

---

## 🔧 Troubleshooting

| Problem | Check | Fix |
|---------|-------|-----|
| No logs | LOG_LEVEL env var | `export LOG_LEVEL=INFO` |
| High latency | by_endpoint stats | Scale more replicas or check model |
| High errors | by_status_code, logs | Check API logs for stack traces |
| Empty metrics | total_requests | Make some requests first |

---

## 📚 Full Documentation

See [MONITORING_LOGGING_GUIDE.md](MONITORING_LOGGING_GUIDE.md) for complete details.
