# Performance Tracking Guide (Post-Deployment)

## Overview

The Performance Tracking system enables you to monitor model performance in production by collecting predictions, true labels, and automatically calculating comprehensive performance metrics and drift detection indicators.

**Key Capabilities:**
- ✅ Record predictions with metadata (confidence, inference time, model version)
- ✅ Submit true labels asynchronously for any prediction
- ✅ Calculate comprehensive performance metrics (accuracy, precision, recall, F1, confusion matrix)
- ✅ Automatic drift detection (accuracy drop, confidence drop, class distribution shift)
- ✅ Query predictions with flexible filtering
- ✅ Export predictions to CSV for analysis
- ✅ Thread-safe with bounded memory footprint

---

## Quick Start

### 1. Start the API with Performance Tracking

```bash
cd mlops-assignment2-new
python -m src.api
```

The API will start at `http://localhost:8000` with all performance tracking endpoints ready.

### 2. Record Predictions

```bash
# Option A: Manual prediction recording (via API)
curl -X POST "http://localhost:8000/predictions/record" \
  -H "Content-Type: application/json" \
  -d '{
    "predicted_class": "cat",
    "confidence": 0.95,
    "model_version": "v1.0",
    "inference_time_ms": 125.5
  }'

# Response: {"prediction_id": "pred_abc123", "status": "recorded"}
```

Or upload an image and predictions are automatically recorded:

```bash
curl -X POST "http://localhost:8000/predict" \
  -F "file=@path/to/image.jpg"

# Response now includes: {"prediction_id": "pred_xyz789", ...}
```

### 3. Provide True Labels

```bash
# Submit ground truth for evaluation
curl -X POST "http://localhost:8000/predictions/pred_abc123/label" \
  -H "Content-Type: application/json" \
  -d '{"true_label": "cat"}'

# Response: {"success": true, "prediction_id": "pred_abc123"}
```

### 4. Get Performance Metrics

```bash
curl -X GET "http://localhost:8000/performance/metrics"

# Response includes:
# {
#   "accuracy": 0.92,
#   "per_class_metrics": {
#     "cat": {"precision": 0.94, "recall": 0.91, "f1": 0.925},
#     "dog": {"precision": 0.90, "recall": 0.93, "f1": 0.915}
#   },
#   "confusion_matrix": {...},
#   "labeled_predictions": 85,
#   "total_predictions": 100
# }
```

### 5. Run Batch Testing

```bash
# Simulate 100 predictions locally with drift detection
python scripts/performance_test.py --mode local --count 100 --drift-demo

# Test against running API
python scripts/performance_test.py --api-url http://localhost:8000 --count 50
```

---

## API Endpoints Reference

### Core Endpoints

#### 1. POST `/predictions/record` - Record a Prediction

Records a new prediction for performance tracking.

**Request:**
```json
{
  "predicted_class": "cat",           // Required: predicted class label
  "confidence": 0.95,                 // Required: confidence score (0-1)
  "image_path": "data/img.jpg",       // Optional: path to image
  "model_version": "v1.0",            // Optional: model version
  "inference_time_ms": 125.5          // Optional: inference time
}
```

**Response:**
```json
{
  "prediction_id": "pred_abc123",
  "status": "recorded"
}
```

**Save the `prediction_id` for later labeling!**

---

#### 2. POST `/predictions/{prediction_id}/label` - Provide Ground Truth

Submit the true label for a recorded prediction.

**Request:**
```json
{
  "true_label": "cat"  // Required: correct class label
}
```

**Response:**
```json
{
  "success": true,
  "prediction_id": "pred_abc123"
}
```

**Example Timing:**
- Record prediction at inference time (immediate)
- Provide true label hours/days later (when ground truth becomes available)

---

#### 3. GET `/performance/metrics` - Get Performance Metrics

Returns comprehensive performance metrics for the model.

**Query Parameters:** None

**Response:**
```json
{
  "accuracy": 0.92,
  "total_predictions": 150,
  "labeled_predictions": 125,
  
  "per_class_metrics": {
    "cat": {
      "precision": 0.94,
      "recall": 0.91,
      "f1": 0.925,
      "tp": 50,
      "fp": 3,
      "fn": 5
    },
    "dog": {
      "precision": 0.90,
      "recall": 0.93,
      "f1": 0.915,
      "tp": 58,
      "fp": 7,
      "fn": 4
    }
  },
  
  "confusion_matrix": {
    "cat": {"cat": 50, "dog": 5},
    "dog": {"cat": 3, "dog": 58}
  },
  
  "confidence_stats": {
    "avg_confidence": 0.876,
    "avg_confidence_correct": 0.89,
    "avg_confidence_incorrect": 0.71
  }
}
```

**Understanding the Metrics:**

| Metric | Meaning | Formula |
|--------|---------|---------|
| **Accuracy** | Overall correctness | (TP + TN) / All |
| **Precision** | Of predicted positive, how many are actually positive | TP / (TP + FP) |
| **Recall** | Of actual positive, how many we caught | TP / (TP + FN) |
| **F1** | Harmonic mean of precision and recall | 2 × (P × R) / (P + R) |
| **TP/FP/FN** | True Positive / False Positive / False Negative | From confusion matrix |

---

#### 4. GET `/performance/drift` - Detect Model Drift

Detects whether the model's performance or behavior has changed.

**Query Parameters:**
- `window_size` (int, default 100): Number of recent predictions to analyze

**Response:**
```json
{
  "drift_detected": false,
  "reasons": [],
  
  "recent_window": {
    "accuracy": 0.93,
    "avg_confidence": 0.88,
    "count": 100
  },
  
  "older_window": {
    "accuracy": 0.92,
    "avg_confidence": 0.87,
    "count": 100
  },
  
  "accuracy_change": 0.01,
  "confidence_change": 0.01
}
```

**Drift Detection Thresholds:**
- 🔴 Accuracy drop > 5% → Drift detected
- 🔴 Confidence drop > 5% → Drift detected  
- 🔴 Class distribution shift > 10% → Drift detected

---

#### 5. GET `/predictions` - Query Predictions

Retrieve recorded predictions with optional filters.

**Query Parameters:**
- `limit` (int, default 100): Max predictions to return
- `unlabeled_only` (bool, default false): Only unlabeled predictions
- `class_filter` (str, optional): Filter by predicted class

**Response:**
```json
{
  "predictions": [
    {
      "prediction_id": "pred_abc123",
      "timestamp": "2024-01-15T10:30:45.123456",
      "predicted_class": "cat",
      "confidence": 0.95,
      "true_label": "cat",
      "model_version": "v1.0",
      "inference_time_ms": 125.5
    },
    ...
  ],
  "count": 87
}
```

**Examples:**
```bash
# Get last 100 predictions
curl "http://localhost:8000/predictions?limit=100"

# Get only unlabeled predictions (to prioritize labeling)
curl "http://localhost:8000/predictions?unlabeled_only=true"

# Get all cat predictions
curl "http://localhost:8000/predictions?class_filter=cat"
```

---

#### 6. POST `/performance/export` - Export to CSV

Export all predictions to CSV for analysis.

**Query Parameters:**
- `filepath` (str, default "predictions.csv"): Output file path

**Response:**
```json
{
  "filepath": "predictions.csv",
  "status": "exported"
}
```

**CSV Format:**
```csv
prediction_id,timestamp,predicted_class,confidence,true_label,model_version,inference_time_ms
pred_abc123,2024-01-15T10:30:45.123456,cat,0.95,cat,v1.0,125.5
pred_def456,2024-01-15T10:31:12.654321,dog,0.87,dog,v1.0,118.2
...
```

---

#### 7. POST `/performance/reset` - Clear All Data

⚠️ **WARNING: This cannot be undone. Export data first if needed!**

Clears all recorded predictions and performance data.

**Response:**
```json
{
  "status": "success",
  "message": "All performance data has been cleared"
}
```

---

## Workflow Examples

### Example 1: Post-Deployment Evaluation

**Scenario:** Deploy model to production and evaluate performance over first 100 requests.

```bash
# 1. Model runs for a while, automatically recording predictions
#    (Each call to /predict returns prediction_id)

# 2. Later, collect ground truth (from user feedback or manual labeling)
for pred_id in pred_001 pred_002 pred_003; do
  curl -X POST "http://localhost:8000/predictions/$pred_id/label" \
    -H "Content-Type: application/json" \
    -d '{"true_label": "cat"}'
done

# 3. Check metrics
curl "http://localhost:8000/performance/metrics" | python -m json.tool

# 4. Export for analysis
curl -X POST "http://localhost:8000/performance/export?filepath=eval_report.csv"
```

---

### Example 2: Continuous Monitoring with Drift Detection

**Scenario:** Monitor model for performance degradation.

```bash
# Every hour, check for drift
curl "http://localhost:8000/performance/drift?window_size=500" \
  | python -m json.tool

# If drift detected:
# 1. Alert the team
# 2. Check predictions: curl "http://localhost:8000/predictions?limit=100"
# 3. Retrain or rollback model
```

---

### Example 3: Batch Testing and Simulation

**Scenario:** Test performance tracking with simulated data.

```bash
# Simulate 100 predictions locally
python scripts/performance_test.py --mode local --count 100

# Test against running API
python scripts/performance_test.py --api-url http://localhost:8000 --count 50

# Simulate drift scenario
python scripts/performance_test.py --mode local --drift-demo --count 200
```

**Output includes:**
- Recording progress
- Metrics display (accuracy, precision, recall, F1)
- Drift detection results
- CSV export status

---

## Performance Tracking Architecture

### Core Components

#### 1. **PerformanceTracker** (`src/performance.py`)
- Stores predictions in memory
- Thread-safe with locks
- Circular buffer (max 10,000 predictions)
- Automatic metrics calculation

#### 2. **Prediction Data Class** 
```python
@dataclass
class Prediction:
    timestamp: str           # ISO format timestamp
    prediction_id: str       # Unique identifier
    predicted_class: str     # Predicted class label
    confidence: float        # Confidence score (0-1)
    true_label: Optional[str]  # Ground truth (filled later)
    model_version: Optional[str]  # Model version
    inference_time_ms: Optional[float]  # Inference time
```

#### 3. **API Integration** (`src/api.py`)
- All endpoints integrated into FastAPI
- Logging middleware tracks all operations
- Thread-safe access to tracker

### Memory Management

```
┌─────────────────────────────────────┐
│   PerformanceTracker                │
│  (Thread-safe Storage)              │
├─────────────────────────────────────┤
│ Circular Buffer (Max 10,000)        │
│  - Newest predictions at end        │
│  - Oldest evicted when full         │
│  - O(1) lookup by prediction_id     │
├─────────────────────────────────────┤
│ Metrics Cache (Calculated on-demand)│
│  - Accuracy, Precision, Recall, F1  │
│  - Per-class confusion matrix       │
│  - Drift indicators                 │
└─────────────────────────────────────┘
```

---

## Monitoring Best Practices

### 1. **Labeling Strategy**

Don't wait to label all predictions—track as you go:

```python
# Immediate (inference)
pred_id = tracker.record_prediction(pred_class, confidence)

# Later (when ground truth available)
tracker.provide_true_label(pred_id, ground_truth)
```

**Typical timeline:**
- T+0: Prediction recorded (user sees result)
- T+1 day: User provides feedback → label submitted
- T+7 days: Enough labels → evaluate performance

### 2. **Drift Monitoring Frequency**

| Scenario | Window Size | Check Frequency |
|----------|------------|-----------------|
| Low-traffic API | 100-500 | Every 8 hours |
| Medium-traffic | 500-2000 | Every 4 hours |
| High-traffic | 2000+ | Every hour |

### 3. **Alerting Rules**

```
IF metrics.accuracy < baseline - 0.05:
  ALERT: "Accuracy dropped by >5%"
  
IF drift_indicators.drift_detected:
  ACTION: Review recent predictions
  CHECK: Class distribution changes
  
IF labeled_predictions < 0.5 * total_predictions:
  REMIND: "Get more ground truth labels"
```

### 4. **Maintenance**

```bash
# Export regularly for backup analysis
curl -X POST "http://localhost:8000/performance/export?filepath=backup_$(date +%Y%m%d).csv"

# Reset periodically to keep memory bounded
# (after exporting if you want historical data)
curl -X POST "http://localhost:8000/performance/reset"
```

---

## Integration with Monitoring & Logging

### Performance Tracking + Monitoring Middleware

The performance tracker integrates with the monitoring system:

```
User Request
    ↓
[LoggingMiddleware]  ← Logs request/response
    ↓
API Endpoint
    ↓
[Model Inference]  ← Tracked for latency
    ↓
[tracker.record_prediction()]  ← Performance tracking
    ↓
Returns prediction_id
```

### Checking Integrated Metrics

```bash
# Get API metrics (requests, latency, errors)
curl "http://localhost:8000/metrics" | python -m json.tool

# Get performance metrics (accuracy, drift, etc)
curl "http://localhost:8000/performance/metrics" | python -m json.tool

# Both systems complement each other:
# - Monitoring: "API is slow" (infrastructure level)
# - Performance: "Model accuracy dropped" (model level)
```

---

## Troubleshooting

### Q: Prediction records don't appear in metrics?
**A:** Ensure you're providing true labels. Metrics only calculated from labeled predictions.

```bash
# Check how many are labeled
curl "http://localhost:8000/performance/metrics" | grep labeled_predictions

# Get unlabeled predictions to label
curl "http://localhost:8000/predictions?unlabeled_only=true"
```

### Q: Drift always detected?
**A:** Check your thresholds. Default: 5% accuracy drop, 5% confidence drop.

```bash
# Get recent drift indicators
curl "http://localhost:8000/performance/drift?window_size=100" | python -m json.tool

# Compare recent vs older windows
# If change < 5%, drift shouldn't trigger
```

### Q: Memory usage growing unbounded?
**A:** The tracker automatically limits to 10,000 predictions. Export and reset periodically.

```bash
# Export (preserves data)
curl -X POST "http://localhost:8000/performance/export?filepath=old_data.csv"

# Reset (clears all)
curl -X POST "http://localhost:8000/performance/reset"
```

### Q: Predictions not recorded from /predict endpoint?
**A:** Check that the API was rebuilt after changes. The prediction recording is automatic.

```bash
# Verify recorder is working
curl -X POST "http://localhost:8000/predictions/record" \
  -H "Content-Type: application/json" \
  -d '{"predicted_class": "cat", "confidence": 0.9}'
```

---

## Performance Tracking Quick Reference

| Task | Endpoint | Method |
|------|----------|--------|
| Record prediction | `/predictions/record` | POST |
| Provide label | `/predictions/{id}/label` | POST |
| Get metrics | `/performance/metrics` | GET |
| Check drift | `/performance/drift` | GET |
| Query predictions | `/predictions` | GET |
| Export data | `/performance/export` | POST |
| Reset data | `/performance/reset` | POST |

---

## Next Steps

1. **Deploy the API** with performance tracking enabled
2. **Configure labeling workflow** (how team provides ground truth)
3. **Set up alerting** for drift detection
4. **Monitor weekly** with metrics and drift checks
5. **Retrain periodically** when drift detected or accuracy drops

---

## Additional Resources

- **Monitoring Guide:** See `MONITORING_LOGGING_GUIDE.md` for request/response logging
- **Deployment Guide:** See `CD_DEPLOYMENT_GUIDE.md` for production deployment
- **Testing:** Run `python scripts/performance_test.py --help` for options

---

*Last Updated: January 2024*
*MLOps Assignment 2 - Model Performance Tracking*
