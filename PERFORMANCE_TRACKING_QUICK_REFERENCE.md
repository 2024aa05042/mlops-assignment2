# Performance Tracking - Quick Reference

## 60-Second Quick Start

```bash
# 1. Start API
python -m src.api

# 2. In another terminal, record prediction
curl -X POST "http://localhost:8000/predictions/record" \
  -H "Content-Type: application/json" \
  -d '{"predicted_class": "cat", "confidence": 0.95}'
# Response: {"prediction_id": "pred_xyz"}

# 3. Provide true label
curl -X POST "http://localhost:8000/predictions/pred_xyz/label" \
  -H "Content-Type: application/json" \
  -d '{"true_label": "cat"}'

# 4. Get metrics
curl "http://localhost:8000/performance/metrics"

# 5. Run batch test
python scripts/performance_test.py --mode local --count 100
```

---

## Core Endpoints (Cheatsheet)

### Record Predictions
```bash
curl -X POST "http://localhost:8000/predictions/record" \
  -H "Content-Type: application/json" \
  -d '{
    "predicted_class": "STRING",      # Required
    "confidence": 0.0-1.0,             # Required
    "model_version": "v1.0",           # Optional
    "inference_time_ms": 125.5         # Optional
  }'
```

### Provide Ground Truth Labels
```bash
curl -X POST "http://localhost:8000/predictions/{PREDICTION_ID}/label" \
  -H "Content-Type: application/json" \
  -d '{"true_label": "STRING"}'
```

### Get Performance Metrics
```bash
curl "http://localhost:8000/performance/metrics"
# Returns: accuracy, precision, recall, F1, confusion matrix, per-class metrics
```

### Detect Drift
```bash
curl "http://localhost:8000/performance/drift?window_size=100"
# Returns: drift_detected, reasons, recent vs older window comparison
```

### Query Predictions
```bash
# All predictions
curl "http://localhost:8000/predictions?limit=100"

# Only unlabeled
curl "http://localhost:8000/predictions?unlabeled_only=true"

# Only "cat" predictions
curl "http://localhost:8000/predictions?class_filter=cat"
```

### Export to CSV
```bash
curl -X POST "http://localhost:8000/performance/export?filepath=data.csv"
```

### Reset Data
```bash
curl -X POST "http://localhost:8000/performance/reset"
# ⚠️ Cannot be undone! Export first if needed.
```

---

## Python Usage (Local Mode)

```python
from src.performance import tracker

# Record prediction
pred_id = tracker.record_prediction(
    predicted_class="cat",
    confidence=0.95,
    model_version="v1.0",
    inference_time_ms=125.5
)

# Provide true label
tracker.provide_true_label(pred_id, "cat")

# Get metrics
metrics = tracker.calculate_metrics()
print(f"Accuracy: {metrics['accuracy']:.2%}")
print(f"Precision (cat): {metrics['per_class_metrics']['cat']['precision']:.4f}")

# Detect drift
drift = tracker.get_drift_indicators(window_size=100)
if drift['drift_detected']:
    print(f"Drift detected! Reasons: {drift['reasons']}")

# Export
filepath = tracker.save_to_csv("predictions.csv")
print(f"Exported to {filepath}")

# Get predictions
unlabeled = tracker.get_predictions(unlabeled_only=True)
print(f"Need to label: {len(unlabeled)} predictions")

# Reset when needed
tracker.reset()
```

---

## Batch Testing

### Simulate Predictions Locally
```bash
python scripts/performance_test.py --mode local --count 100
```

### Test Against Running API
```bash
python scripts/performance_test.py --api-url http://localhost:8000 --count 50
```

### Simulate Model Drift
```bash
python scripts/performance_test.py --mode local --drift-demo
```

---

## Key Metrics Explained

| Metric | Range | Interpretation |
|--------|-------|-----------------|
| **Accuracy** | 0.0-1.0 | % of correct predictions |
| **Precision** | 0.0-1.0 | Of predicted positive, % actually positive |
| **Recall** | 0.0-1.0 | Of actual positive, % we caught |
| **F1** | 0.0-1.0 | Balance between precision & recall |
| **Confidence** | 0.0-1.0 | Model's certainty in prediction |

### Example Interpretation
```
Accuracy: 0.92  → 92% correct predictions
Precision (cat): 0.94  → When we say "cat", 94% right
Recall (cat): 0.91  → Of all actual cats, we catch 91%
F1: 0.925  → Good balance (0.925 = harmonic mean)
```

---

## Drift Detection

### What is Drift?
Model performance changes in production (usually degrades).

### Detection Thresholds
- 🔴 Accuracy drops >5% from older window → **DRIFT**
- 🔴 Confidence drops >5% → **DRIFT**
- 🔴 Class distribution shifts >10% → **DRIFT**

### Example Response
```json
{
  "drift_detected": true,
  "reasons": [
    "Accuracy changed from 0.92 to 0.87 (-0.05)",
    "Class distribution cat: 60% → 45%"
  ],
  "recent_window": {"accuracy": 0.87, "count": 100},
  "older_window": {"accuracy": 0.92, "count": 100}
}
```

### How to Respond to Drift
1. ✅ Export prediction data for analysis
2. ✅ Check recent predictions for patterns
3. ✅ Review labeling quality
4. ✅ Consider retraining model
5. ✅ Consider rolling back to previous version

---

## Common Workflows

### Workflow 1: Daily Monitoring
```bash
# Morning check
curl "http://localhost:8000/performance/metrics" | grep accuracy

# Check for drift
curl "http://localhost:8000/performance/drift?window_size=500" | grep drift_detected

# If drift: export and investigate
curl -X POST "http://localhost:8000/performance/export?filepath=daily_report.csv"
```

### Workflow 2: Labeling Pipeline
```bash
# Get unlabeled predictions
curl "http://localhost:8000/predictions?unlabeled_only=true&limit=50"

# Team labels them (get true labels from users/reviewers)
# Submit labels
for pred_id in $(cat labeled_predictions.txt); do
  true_label=$(get_label_from_file $pred_id)
  curl -X POST "http://localhost:8000/predictions/$pred_id/label" \
    -H "Content-Type: application/json" \
    -d "{\"true_label\": \"$true_label\"}"
done

# Check new metrics
curl "http://localhost:8000/performance/metrics"
```

### Workflow 3: Model Retraining
```bash
# Export current performance data
curl -X POST "http://localhost:8000/performance/export?filepath=pre_retrain.csv"

# Retrain model with misclassified samples
# Deploy new model and reset tracker
curl -X POST "http://localhost:8000/performance/reset"

# Start tracking new model version
curl -X POST "http://localhost:8000/predictions/record" \
  -H "Content-Type: application/json" \
  -d '{"predicted_class": "cat", "confidence": 0.96, "model_version": "v2.0"}'
```

---

## Performance Tracker Architecture

```
              ┌─────────────────────┐
              │   REST API          │
              │  (6 endpoints)      │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Logging Middleware  │
              │  (Request/Response) │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────────────────┐
              │  /predict (Auto-Record)         │
              │  /predictions/record (Manual)   │
              │  /predictions/{id}/label        │
              │  /performance/* (Query/Analyze) │
              └──────────┬──────────────────────┘
                         │
              ┌──────────▼──────────────────────┐
              │   PerformanceTracker            │
              │   (Thread-Safe Storage)         │
              │   - Circular Buffer (10K)       │
              │   - Metrics Calculation         │
              │   - Drift Detection             │
              │   - CSV Export                  │
              └─────────────────────────────────┘
```

---

## File Locations

| File | Purpose |
|------|---------|
| `src/performance.py` | Core performance tracking module |
| `src/api.py` | FastAPI with performance endpoints |
| `scripts/performance_test.py` | Batch testing script |
| `PERFORMANCE_TRACKING_GUIDE.md` | Full documentation |
| `PERFORMANCE_TRACKING_QUICK_REFERENCE.md` | This file |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Metrics show 0.0 accuracy | No labeled predictions. Use `/predictions/{id}/label` to label |
| Drift always detected | Check window size, default uses last 100 predictions |
| Memory keeps growing | Use `/performance/reset` or export periodically |
| API returns 404 | Ensure prediction_id from `/predictions/record` response |
| Slow metrics calculation | Too many predictions. Export and reset to manage memory |

---

## Environment Variables

```bash
# Logging level
export LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR

# Performance tracking size (in code only, not configurable yet)
# MAX_PREDICTIONS = 10000      # Maximum stored predictions
# DRIFT_ACCURACY_THRESHOLD = 0.05   # 5% accuracy change
# DRIFT_CONFIDENCE_THRESHOLD = 0.05 # 5% confidence change
```

---

## Real-World Example: Small Batch Collection

```bash
#!/bin/bash
# Collect 50 predictions with labels

echo "Recording 50 predictions..."
pred_ids=()

# Record predictions (simulate from API)
for i in {1..50}; do
  response=$(curl -s -X POST "http://localhost:8000/predictions/record" \
    -H "Content-Type: application/json" \
    -d "{
      \"predicted_class\": \"$([ $((RANDOM % 2)) -eq 0 ] && echo 'cat' || echo 'dog')\",
      \"confidence\": 0.$(($RANDOM % 100)),
      \"model_version\": \"v1.0\",
      \"inference_time_ms\": $((($RANDOM % 200) + 50))
    }")
  
  pred_id=$(echo $response | jq -r '.prediction_id')
  pred_ids+=($pred_id)
  echo "  [$i/50] Recorded prediction: $pred_id"
done

echo ""
echo "Providing ground truth labels..."

# Provide labels (simulating ground truth collection)
for pred_id in "${pred_ids[@]}"; do
  true_label="$([ $((RANDOM % 2)) -eq 0 ] && echo 'cat' || echo 'dog')"
  
  curl -s -X POST "http://localhost:8000/predictions/$pred_id/label" \
    -H "Content-Type: application/json" \
    -d "{\"true_label\": \"$true_label\"}" > /dev/null
  
  echo "  Labeled: $pred_id → $true_label"
done

echo ""
echo "Getting metrics..."
curl -s "http://localhost:8000/performance/metrics" | jq .

echo ""
echo "Done!"
```

Execute with: `bash scripts/collect_batch.sh`

---

## Integration Checklist

- [ ] API running with `/predict` endpoint returning `prediction_id`
- [ ] Performance tracker imported in `src/api.py`
- [ ] All 6 performance endpoints available
- [ ] Monitoring middleware logging requests
- [ ] Performance test script working (`performance_test.py`)
- [ ] API returning metrics with accuracy >0.8
- [ ] Drift detection functional (test with `--drift-demo`)
- [ ] CSV export working (check file created)
- [ ] Documentation reviewed (this file + full guide)

---

## Performance Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| Record prediction | <1ms | In-memory, O(1) |
| Provide label | <1ms | In-memory, O(1) |
| Calculate metrics | 10-50ms | O(n), n=predictions |
| Detect drift | 10-50ms | O(n), analyzes 2 windows |
| Export to CSV | 50-200ms | File I/O, n=predictions |
| Query predictions | 1-10ms | O(1) to O(n) based on filter |

---

*Performance Tracking Quick Reference*
*MLOps Assignment 2*
*Last Updated: January 2024*
