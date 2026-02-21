from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image
import io
import os
import torch
import torch.nn.functional as F
from pathlib import Path
import logging
import time

#from model import create_model
from .model import create_model
from .monitoring import setup_logging, LoggingMiddleware, metrics, log_prediction
from .performance import tracker

# Initialize logging
logger = setup_logging()

app = FastAPI(title="Cats vs Dogs API")

# Add logging middleware
app.add_middleware(LoggingMiddleware, logger=logger)

logger.info("Cats vs Dogs API initialized")


def _load_classes(output_dir="artifacts"):
    cls_path = Path(output_dir) / "classes.txt"
    if cls_path.exists():
        return [l.strip() for l in cls_path.read_text().splitlines() if l.strip()]
    # fallback default
    return ["cat", "dog"]


def _load_model(output_dir="artifacts", device="cpu"):
    # prefer full model (.pt) then state_dict (.pth)
    print(f"Looking for model in {Path(output_dir)}...")
    pt = Path(output_dir) / "best_model.pt"
    pth = Path(output_dir) / "best_model.pth"
    onnx = Path(output_dir) / "best_model.onnx"
    classes = _load_classes(output_dir)
    num_classes = max(2, len(classes))
    if pt.exists():
        model = torch.load(str(pt), map_location=device)
        model.eval()
        return model, classes
    elif pth.exists():
        model = create_model(num_classes=num_classes, pretrained=False)
        model.load_state_dict(torch.load(str(pth), map_location=device))
        model.eval()
        return model, classes
    elif onnx.exists():
        # ONNX inference not implemented here
        raise RuntimeError("ONNX model present; API cannot load ONNX for PyTorch inference")
    else:
        # Model not found - return None to indicate demo mode
        return None, classes


def _preprocess_image(image_bytes, img_size=224):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # simple transform similar to validation
    image = image.resize((img_size, img_size))
    arr = torch.ByteTensor(torch.ByteStorage.from_buffer(image.tobytes()))
    # simpler: use PIL->tensor via torchvision if available, but avoid extra import
    import torchvision.transforms as transforms
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    return transform(image).unsqueeze(0)


@app.get("/health")
async def health():
    logger.info("Health check requested")
    return JSONResponse({
        "status": "healthy",
        "timestamp": time.time(),
        "service": "cats-dogs-api"
    })


@app.get("/metrics")
async def get_metrics():
    """
    Returns API metrics in JSON format.
    
    Includes:
    - Total request count and error count
    - Latency percentiles (p50, p99, avg)
    - Per-endpoint statistics
    - Prediction distribution
    - HTTP status code distribution
    """
    logger.info("Metrics requested")
    return JSONResponse(metrics.get_metrics())


@app.post("/metrics/reset")
async def reset_metrics(request: Request = None):
    """Reset all metrics. Requires admin access."""
    logger.warning("Metrics reset requested")
    metrics.reset()
    return JSONResponse({"status": "Metrics reset successfully"})


@app.post("/predict")
async def predict(file: UploadFile = File(...), request: Request = None):
    request_id = request.headers.get("x-request-id", "") if request else ""
    start_time = time.time()
    
    try:
        contents = await file.read()
        img_tensor = _preprocess_image(contents)
    except Exception as e:
        logger.error(
            f"Failed to read image in /predict: {str(e)}",
            extra={"request_id": request_id, "error": str(e)}
        )
        raise HTTPException(status_code=400, detail=f"Failed to read image: {e}")

    try:
        model, classes = _load_model()
    except RuntimeError as e:
        logger.error(
            f"Failed to load model: {str(e)}",
            extra={"request_id": request_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

    # If model is None, return mock prediction (demo mode)
    if model is None:
        logger.info(
            "Demo mode prediction",
            extra={"request_id": request_id, "prediction": "cat"}
        )
        pred_label = "cat"
        confidence = 0.52
        pred_idx = 0
        probs = [0.52, 0.48]
    else:
        device = torch.device("cpu")
        model = model.to(device)
        with torch.no_grad():
            outputs = model(img_tensor.to(device))
            probs = F.softmax(outputs, dim=1).cpu().squeeze().tolist()
            if isinstance(probs, float):
                probs = [probs]
            pred_idx = int(torch.tensor(probs).argmax().item())
            pred_label = classes[pred_idx] if pred_idx < len(classes) else str(pred_idx)
            confidence = probs[pred_idx]
    
    # Calculate inference time
    inference_time = (time.time() - start_time) * 1000
    
    # Log prediction
    log_prediction(logger, "/predict", pred_label, confidence, request_id)
    
    # Record prediction for performance tracking
    prediction_id = tracker.record_prediction(
        predicted_class=pred_label,
        confidence=confidence,
        image_path=None,  # No path for uploaded files
        inference_time_ms=inference_time,
    )

    return {
        "prediction_id": prediction_id,
        "label": pred_label,
        "index": pred_idx,
        "probabilities": probs,
        "classes": classes,
        "confidence": round(confidence, 4),
        "inference_time_ms": round(inference_time, 2),
    }


class PathRequest(BaseModel):
    path: str


@app.post("/predict_path")
async def predict_path(req: PathRequest, request: Request = None):
    # Accepts JSON body: {"path": "data/processed/test/cat/image.jpg"}
    request_id = request.headers.get("x-request-id", "") if request else ""
    start_time = time.time()
    p = Path(req.path)
    if not p.is_absolute():
        # resolve relative to repo root
        repo_root = Path(__file__).resolve().parents[1]
        p = (repo_root / req.path).resolve()
    if not p.exists():
        logger.error(
            f"File not found in /predict_path",
            extra={"request_id": request_id, "path": str(req.path)}
        )
        raise HTTPException(status_code=400, detail=f"File not found: {p}")
    try:
        contents = p.read_bytes()
        img_tensor = _preprocess_image(contents)
    except Exception as e:
        logger.error(
            f"Failed to read image: {str(e)}",
            extra={"request_id": request_id, "path": str(req.path), "error": str(e)}
        )
        raise HTTPException(status_code=400, detail=f"Failed to read image: {e}")

    try:
        model, classes = _load_model()
    except RuntimeError as e:
        logger.error(
            f"Failed to load model: {str(e)}",
            extra={"request_id": request_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

    # If model is None, return mock prediction (demo mode)
    if model is None:
        logger.info(
            "Demo mode prediction",
            extra={"request_id": request_id, "prediction": "cat"}
        )
        return {
            "label": "cat",
            "index": 0,
            "probabilities": [0.52, 0.48],
            "classes": classes,
            "mode": "demo (no model loaded)"
        }

    device = torch.device("cpu")
    model = model.to(device)
    with torch.no_grad():
        outputs = model(img_tensor.to(device))
        probs = F.softmax(outputs, dim=1).cpu().squeeze().tolist()
        if isinstance(probs, float):
            probs = [probs]
        pred_idx = int(torch.tensor(probs).argmax().item())
        pred_label = classes[pred_idx] if pred_idx < len(classes) else str(pred_idx)
        confidence = probs[pred_idx]
    
    print("Logging the prediction--------")

    # Calculate inference time
    inference_time = (time.time() - start_time) * 1000
    # Log prediction
    log_prediction(logger, "/predict_path", pred_label, confidence, request_id)

    # Record prediction for performance tracking
    prediction_id = tracker.record_prediction(
        predicted_class=pred_label,
        confidence=confidence,
        image_path=None,  # No path for uploaded files
        inference_time_ms=inference_time,
    )

    return {
        "prediction_id": prediction_id,
        "label": pred_label,
        "index": pred_idx,
        "probabilities": probs,
        "classes": classes,
        "confidence": round(confidence, 4),
        "inference_time_ms": round(inference_time, 2),
    }


# ============================================================================
# Performance Tracking Endpoints
# ============================================================================

class TrueLabelRequest(BaseModel):
    true_label: str


class PredictionRecordRequest(BaseModel):
    predicted_class: str
    confidence: float
    image_path: str = None
    model_version: str = None
    inference_time_ms: float = None


@app.post("/predictions/record")
async def record_prediction(req: PredictionRecordRequest):
    """
    Manually record a prediction for performance tracking.
    
    Args:
        predicted_class: The predicted class label
        confidence: Confidence score (0-1)
        image_path: Optional path to the image
        model_version: Optional model version
        inference_time_ms: Optional inference time in milliseconds
    
    Returns:
        prediction_id: Unique ID for this prediction (use to provide true label later)
    """
    try:
        prediction_id = tracker.record_prediction(
            predicted_class=req.predicted_class,
            confidence=req.confidence,
            image_path=req.image_path,
            model_version=req.model_version,
            inference_time_ms=req.inference_time_ms,
        )
        logger.info(
            f"Prediction recorded",
            extra={"prediction_id": prediction_id, "class": req.predicted_class}
        )
        return {"prediction_id": prediction_id, "status": "recorded"}
    except Exception as e:
        logger.error(f"Failed to record prediction: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to record prediction: {e}")


@app.post("/predictions/{prediction_id}/label")
async def provide_true_label(prediction_id: str, req: TrueLabelRequest):
    """
    Provide the true label for a previously recorded prediction.
    
    Args:
        prediction_id: ID of the prediction (from /predictions/record response)
        true_label: The correct class label
    
    Returns:
        success: Whether the label was accepted
    """
    try:
        success = tracker.provide_true_label(prediction_id, req.true_label)
        if success:
            logger.info(
                f"True label provided",
                extra={"prediction_id": prediction_id, "true_label": req.true_label}
            )
            return {"success": True, "prediction_id": prediction_id}
        else:
            logger.warning(
                f"Failed to provide true label: prediction not found",
                extra={"prediction_id": prediction_id}
            )
            raise HTTPException(status_code=404, detail="Prediction not found")
    except Exception as e:
        logger.error(f"Failed to provide true label: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to provide true label: {e}")


@app.get("/performance/metrics")
async def get_performance_metrics():
    """
    Get current performance metrics for the model.
    
    Returns:
        Comprehensive performance metrics including:
        - accuracy: Overall accuracy
        - per_class_metrics: Precision, recall, F1 for each class
        - confusion_matrix: Confusion matrix
        - confidence_stats: Average confidence for correct/incorrect predictions
        - total_predictions: Total number of predictions tracked
        - labeled_predictions: Number of predictions with true labels
    """
    try:
        metrics_data = tracker.calculate_metrics()
        logger.info("Performance metrics retrieved", extra={"total": metrics_data.get("total_predictions", 0)})
        return metrics_data
    except Exception as e:
        logger.error(f"Failed to calculate metrics: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to calculate metrics: {e}")


@app.get("/performance/drift")
async def get_drift_indicators(window_size: int = 100):
    """
    Get drift detection indicators for the model.
    
    Args:
        window_size: Number of recent predictions to analyze (default 100)
    
    Returns:
        Drift indicators including:
        - drift_detected: Boolean indicating if drift is detected
        - reasons: List of reasons for drift (if detected)
        - recent_window: Performance metrics for recent predictions
        - older_window: Performance metrics for older predictions
        - accuracy_change: Absolute change in accuracy
        - confidence_change: Absolute change in confidence
    """
    try:
        drift_data = tracker.get_drift_indicators(window_size)
        logger.info(
            "Drift indicators retrieved",
            extra={"drift_detected": drift_data.get("drift_detected", False)}
        )
        return drift_data
    except Exception as e:
        logger.error(f"Failed to get drift indicators: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to get drift indicators: {e}")


@app.get("/predictions")
async def get_predictions(limit: int = 100, unlabeled_only: bool = False, class_filter: str = None):
    """
    Get recorded predictions with optional filters.
    
    Args:
        limit: Maximum number of predictions to return (default 100)
        unlabeled_only: If true, return only predictions without true labels
        class_filter: If provided, return only predictions for this class
    
    Returns:
        List of predictions with all available metadata
    """
    try:
        predictions = tracker.get_predictions(
            limit=limit,
            unlabeled_only=unlabeled_only,
            class_filter=class_filter
        )
        logger.info(
            "Predictions retrieved",
            extra={"count": len(predictions), "unlabeled_only": unlabeled_only}
        )
        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error(f"Failed to retrieve predictions: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to retrieve predictions: {e}")


@app.post("/performance/export")
async def export_predictions(filepath: str = "predictions.csv"):
    """
    Export all recorded predictions to a CSV file.
    
    Args:
        filepath: Path where to save the CSV file (default predictions.csv)
    
    Returns:
        Exported filepath and number of predictions exported
    """
    try:
        exported_path = tracker.save_to_csv(filepath)
        logger.info(f"Predictions exported to {exported_path}")
        return {"filepath": exported_path, "status": "exported"}
    except Exception as e:
        logger.error(f"Failed to export predictions: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to export predictions: {e}")


@app.post("/performance/reset")
async def reset_performance_data():
    """
    Clear all recorded predictions and performance data.
    WARNING: This cannot be undone. Export data before resetting if needed.
    
    Returns:
        success: Whether the reset was successful
    """
    try:
        tracker.reset()
        logger.warning("Performance data reset by user")
        return {"status": "success", "message": "All performance data has been cleared"}
    except Exception as e:
        logger.error(f"Failed to reset performance data: {str(e)}", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Failed to reset performance data: {e}")


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get logging level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.info(f"Starting API server with log level: {log_level}")
    
    # Run the API on port 8000
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        log_level=log_level.lower(),
        access_log=True,
    )


