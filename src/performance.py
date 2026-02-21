"""
Model Performance Tracking - Post-Deployment

Tracks predictions and their ground truth labels to evaluate model performance
in production. Useful for detecting model drift and monitoring accuracy.

Features:
- Store predictions with metadata (timestamp, image path, prediction, confidence)
- Accept true labels for any prediction
- Calculate performance metrics (accuracy, precision, recall, F1, confusion matrix)
- Support both real predictions and simulated test data
- Thread-safe storage
"""

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
from collections import defaultdict
import logging

logger = logging.getLogger("cats-dogs-api")


@dataclass
class Prediction:
    """A single prediction record"""
    timestamp: str
    prediction_id: str
    image_path: Optional[str]
    predicted_class: str
    confidence: float
    true_label: Optional[str] = None
    model_version: Optional[str] = None
    inference_time_ms: Optional[float] = None


class PerformanceTracker:
    """Tracks predictions and evaluates performance metrics"""
    
    def __init__(self, storage_dir: str = "predictions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.lock = threading.Lock()
        self.predictions = []  # List of Prediction objects
        self.label_index = {}  # Map prediction_id -> true_label
        
        # Load existing predictions on startup
        self._load_predictions()
        
        logger.info(f"Performance tracker initialized with {len(self.predictions)} stored predictions")
    
    def record_prediction(
        self,
        predicted_class: str,
        confidence: float,
        image_path: Optional[str] = None,
        model_version: Optional[str] = None,
        inference_time_ms: Optional[float] = None,
    ) -> str:
        """
        Record a prediction.
        
        Returns prediction_id for later reference to provide true label.
        """
        with self.lock:
            timestamp = datetime.utcnow().isoformat() + "Z"
            prediction_id = f"{int(time.time() * 1000000)}"  # microsecond timestamp
            
            prediction = Prediction(
                timestamp=timestamp,
                prediction_id=prediction_id,
                image_path=image_path,
                predicted_class=predicted_class,
                confidence=confidence,
                model_version=model_version,
                inference_time_ms=inference_time_ms,
            )
            
            self.predictions.append(prediction)
            
            # Keep last 10000 predictions to avoid unbounded memory growth
            if len(self.predictions) > 10000:
                self.predictions.pop(0)
            
            logger.info(f"Recorded prediction {prediction_id}: {predicted_class} ({confidence:.4f})")
            
            return prediction_id
    
    def provide_true_label(self, prediction_id: str, true_label: str) -> bool:
        """
        Provide the true label for a prediction.
        
        Returns True if label was updated, False if prediction_id not found.
        """
        with self.lock:
            # Find prediction by ID
            for pred in self.predictions:
                if pred.prediction_id == prediction_id:
                    pred.true_label = true_label
                    logger.info(f"Updated prediction {prediction_id} with true label: {true_label}")
                    return True
            
            logger.warning(f"Prediction {prediction_id} not found for labeling")
            return False
    
    def get_prediction(self, prediction_id: str) -> Optional[Dict[str, Any]]:
        """Get a single prediction by ID"""
        with self.lock:
            for pred in self.predictions:
                if pred.prediction_id == prediction_id:
                    return asdict(pred)
            return None
    
    def get_predictions(
        self,
        limit: int = 100,
        unlabeled_only: bool = False,
        class_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get predictions with optional filters.
        
        Args:
            limit: Max predictions to return
            unlabeled_only: Only return predictions without true labels
            class_filter: Filter by predicted class
        """
        with self.lock:
            results = []
            for pred in reversed(self.predictions):  # Most recent first
                if len(results) >= limit:
                    break
                
                if unlabeled_only and pred.true_label is not None:
                    continue
                
                if class_filter and pred.predicted_class != class_filter:
                    continue
                
                results.append(asdict(pred))
            
            return results
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics for labeled predictions"""
        with self.lock:
            # Filter to only labeled predictions
            labeled = [p for p in self.predictions if p.true_label is not None]
            
            if not labeled:
                return {
                    "status": "No labeled predictions available",
                    "total_predictions": len(self.predictions),
                    "labeled_predictions": 0,
                }
            
            # Calculate metrics
            correct = sum(1 for p in labeled if p.predicted_class == p.true_label)
            accuracy = correct / len(labeled) if labeled else 0
            
            # Per-class metrics
            class_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
            all_classes = set(p.predicted_class for p in labeled) | set(p.true_label for p in labeled)
            
            for pred in labeled:
                for cls in all_classes:
                    if pred.predicted_class == cls and pred.true_label == cls:
                        class_metrics[cls]["tp"] += 1
                    elif pred.predicted_class == cls and pred.true_label != cls:
                        class_metrics[cls]["fp"] += 1
                    elif pred.predicted_class != cls and pred.true_label == cls:
                        class_metrics[cls]["fn"] += 1
                    else:
                        class_metrics[cls]["tn"] += 1
            
            # Calculate precision, recall, F1 for each class
            class_results = {}
            for cls, counts in class_metrics.items():
                tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
                
                class_results[cls] = {
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                }
            
            # Confusion matrix
            confusion_matrix = {}
            for true_cls in all_classes:
                for pred_cls in all_classes:
                    count = sum(
                        1 for p in labeled
                        if p.true_label == true_cls and p.predicted_class == pred_cls
                    )
                    confusion_matrix[f"{true_cls}_as_{pred_cls}"] = count
            
            # Confidence statistics
            avg_confidence = sum(p.confidence for p in labeled) / len(labeled) if labeled else 0
            correct_confidence = sum(
                p.confidence for p in labeled if p.predicted_class == p.true_label
            )
            correct_avg_confidence = correct_confidence / correct if correct > 0 else 0
            
            incorrect_confidence = sum(
                p.confidence for p in labeled if p.predicted_class != p.true_label
            )
            incorrect_avg_confidence = incorrect_confidence / (len(labeled) - correct) if (len(labeled) - correct) > 0 else 0
            
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_predictions": len(self.predictions),
                "labeled_predictions": len(labeled),
                "unlabeled_predictions": len(self.predictions) - len(labeled),
                "accuracy": round(accuracy, 4),
                "correct_predictions": correct,
                "incorrect_predictions": len(labeled) - correct,
                "by_class": class_results,
                "confusion_matrix": confusion_matrix,
                "confidence": {
                    "overall_avg": round(avg_confidence, 4),
                    "correct_predictions_avg": round(correct_avg_confidence, 4),
                    "incorrect_predictions_avg": round(incorrect_avg_confidence, 4),
                },
            }
    
    def get_drift_indicators(self, window_size: int = 100) -> Dict[str, Any]:
        """
        Detect potential model drift by comparing recent vs older predictions.
        
        Returns indicators like:
        - Accuracy drop
        - Prediction distribution shift
        - Confidence drop
        """
        with self.lock:
            if len(self.predictions) < window_size * 2:
                return {"status": "Insufficient data for drift detection"}
            
            # Split into two windows
            all_labeled = [p for p in self.predictions if p.true_label is not None]
            if len(all_labeled) < window_size * 2:
                return {"status": "Insufficient labeled data for drift detection"}
            
            recent = all_labeled[-window_size:]
            older = all_labeled[-(window_size * 2):-window_size]
            
            # Calculate accuracy for each window
            recent_acc = sum(1 for p in recent if p.predicted_class == p.true_label) / len(recent)
            older_acc = sum(1 for p in older if p.predicted_class == p.true_label) / len(older)
            
            # Calculate average confidence for each window
            recent_conf = sum(p.confidence for p in recent) / len(recent)
            older_conf = sum(p.confidence for p in older) / len(older)
            
            # Prediction distribution
            recent_dist = {}
            older_dist = {}
            for cls in set(p.predicted_class for p in recent + older):
                recent_dist[cls] = sum(1 for p in recent if p.predicted_class == cls) / len(recent)
                older_dist[cls] = sum(1 for p in older if p.predicted_class == cls) / len(older)
            
            drift_detected = False
            reasons = []
            
            # Check for accuracy drop > 5%
            acc_drop = older_acc - recent_acc
            if acc_drop > 0.05:
                drift_detected = True
                reasons.append(f"Accuracy dropped {acc_drop:.1%}")
            
            # Check for confidence drop > 5%
            conf_drop = older_conf - recent_conf
            if conf_drop > 0.05:
                drift_detected = True
                reasons.append(f"Average confidence dropped {conf_drop:.1%}")
            
            # Check for class distribution shift > 10%
            for cls in recent_dist:
                dist_shift = abs(recent_dist[cls] - older_dist.get(cls, 0))
                if dist_shift > 0.1:
                    drift_detected = True
                    reasons.append(f"Class '{cls}' distribution shifted {dist_shift:.1%}")
            
            return {
                "drift_detected": drift_detected,
                "reasons": reasons,
                "recent_window": {
                    "accuracy": round(recent_acc, 4),
                    "avg_confidence": round(recent_conf, 4),
                    "distribution": {k: round(v, 4) for k, v in recent_dist.items()},
                },
                "older_window": {
                    "accuracy": round(older_acc, 4),
                    "avg_confidence": round(older_conf, 4),
                    "distribution": {k: round(v, 4) for k, v in older_dist.items()},
                },
            }
    
    def save_to_csv(self, filepath: Optional[str] = None) -> str:
        """
        Export predictions to CSV for analysis.
        
        Returns filepath of saved CSV.
        """
        import csv
        
        if filepath is None:
            filepath = self.storage_dir / f"predictions_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with self.lock:
            with open(filepath, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'timestamp', 'prediction_id', 'image_path', 'predicted_class',
                    'confidence', 'true_label', 'model_version', 'inference_time_ms'
                ])
                writer.writeheader()
                for pred in self.predictions:
                    writer.writerow(asdict(pred))
        
        logger.info(f"Exported {len(self.predictions)} predictions to {filepath}")
        return str(filepath)
    
    def _load_predictions(self):
        """Load previously stored predictions from disk (future enhancement)"""
        # This could load from storage_dir/*.json files
        pass
    
    def reset(self):
        """Reset all predictions"""
        with self.lock:
            self.predictions = []
            self.label_index = {}
        logger.warning("Performance tracker reset - all predictions cleared")


# Global tracker instance
tracker = PerformanceTracker()
