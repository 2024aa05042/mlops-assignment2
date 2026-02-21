"""
Logging and monitoring module for the Cats vs Dogs API.

Provides:
- Structured logging configuration
- Request/response logging middleware
- Metrics collection (counters, latencies)
- Metrics endpoint for Prometheus-style scraping
"""

import logging
import time
import json
from datetime import datetime
from typing import Callable, Dict, Any
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import threading

# Configure structured logging
def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """Initialize structured logging for the application."""
    
    # Create logger
    logger = logging.getLogger("cats-dogs-api")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # Create console handler with JSON formatting
    handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, log_level.upper()))
    
    # Create JSON formatter for structured logging
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


class MetricsCollector:
    """Collects and stores API metrics."""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.request_count = 0
        self.error_count = 0
        self.request_latencies = []  # List of latencies in milliseconds
        self.endpoint_stats = defaultdict(lambda: {
            "count": 0,
            "errors": 0,
            "total_latency": 0,
            "min_latency": float('inf'),
            "max_latency": 0,
        })
        self.prediction_classes = defaultdict(int)  # Count of each prediction class
        self.status_codes = defaultdict(int)  # Count of each HTTP status code
    
    def record_request(self, endpoint: str, status_code: int, latency_ms: float, 
                      prediction_class: str = None, error: bool = False):
        """Record metrics for a request."""
        with self.lock:
            self.request_count += 1
            
            if error:
                self.error_count += 1
            
            # Store raw latency
            self.request_latencies.append(latency_ms)
            
            # Keep only last 1000 latencies to avoid memory bloat
            if len(self.request_latencies) > 1000:
                self.request_latencies.pop(0)
            
            # Update endpoint statistics
            stats = self.endpoint_stats[endpoint]
            stats["count"] += 1
            stats["total_latency"] += latency_ms
            stats["min_latency"] = min(stats["min_latency"], latency_ms)
            stats["max_latency"] = max(stats["max_latency"], latency_ms)
            
            if error:
                stats["errors"] += 1
            
            # Track status codes
            self.status_codes[status_code] += 1
            
            # Track prediction classes
            if prediction_class:
                self.prediction_classes[prediction_class] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot."""
        with self.lock:
            avg_latency = (
                sum(self.request_latencies) / len(self.request_latencies)
                if self.request_latencies else 0
            )
            
            latencies = sorted(self.request_latencies)
            p50 = latencies[len(latencies)//2] if latencies else 0
            p99 = latencies[int(len(latencies)*0.99)] if len(latencies) > 0 else 0
            
            endpoint_stats_normalized = {}
            for endpoint, stats in self.endpoint_stats.items():
                endpoint_stats_normalized[endpoint] = {
                    "count": stats["count"],
                    "errors": stats["errors"],
                    "avg_latency_ms": (
                        stats["total_latency"] / stats["count"]
                        if stats["count"] > 0 else 0
                    ),
                    "min_latency_ms": (
                        stats["min_latency"] if stats["min_latency"] != float('inf') else 0
                    ),
                    "max_latency_ms": stats["max_latency"],
                }
            
            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "total_requests": self.request_count,
                "total_errors": self.error_count,
                "error_rate": (
                    self.error_count / self.request_count
                    if self.request_count > 0 else 0
                ),
                "latency_ms": {
                    "avg": round(avg_latency, 2),
                    "p50": round(p50, 2),
                    "p99": round(p99, 2),
                    "min": round(min(self.request_latencies), 2) if self.request_latencies else 0,
                    "max": round(max(self.request_latencies), 2) if self.request_latencies else 0,
                },
                "by_endpoint": endpoint_stats_normalized,
                "by_status_code": dict(self.status_codes),
                "predictions": dict(self.prediction_classes),
            }
    
    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.request_count = 0
            self.error_count = 0
            self.request_latencies = []
            self.endpoint_stats = defaultdict(lambda: {
                "count": 0,
                "errors": 0,
                "total_latency": 0,
                "min_latency": float('inf'),
                "max_latency": 0,
            })
            self.prediction_classes = defaultdict(int)
            self.status_codes = defaultdict(int)


# Global metrics instance
metrics = MetricsCollector()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all requests and responses."""
    
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log incoming request and outgoing response."""
        
        # Extract request info
        method = request.method
        path = request.url.path
        endpoint = method + " " + path
        
        # Log request (exclude sensitive data)
        request_id = request.headers.get("x-request-id", "")
        
        self.logger.info(
            f"Incoming request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "query": str(request.url.query) if request.url.query else "",
            }
        )
        
        # Record start time
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            error = False
            
        except Exception as e:
            # Handle exceptions
            status_code = 500
            error = True
            self.logger.error(
                f"Request error: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "error": str(e),
                },
                exc_info=True
            )
            raise
        
        finally:
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Log response
            self.logger.info(
                f"Response sent",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": status_code,
                    "latency_ms": round(latency_ms, 2),
                }
            )
            
            # Record metrics
            metrics.record_request(
                endpoint=path,
                status_code=status_code,
                latency_ms=latency_ms,
                error=error
            )
        
        return response


def exclude_sensitive_data(obj: Any, exclude_keys: set = None) -> Any:
    """
    Remove sensitive data from objects before logging.
    
    Excludes: password, token, api_key, secret, etc.
    """
    if exclude_keys is None:
        exclude_keys = {
            'password', 'token', 'api_key', 'secret', 'auth',
            'Authorization', 'X-API-Key', 'cookie', 'credentials'
        }
    
    if isinstance(obj, dict):
        return {
            k: exclude_sensitive_data(v, exclude_keys)
            for k, v in obj.items()
            if k not in exclude_keys
        }
    elif isinstance(obj, (list, tuple)):
        return [exclude_sensitive_data(item, exclude_keys) for item in obj]
    else:
        return obj


def log_prediction(logger: logging.Logger, endpoint: str, prediction_class: str, 
                    confidence: float, request_id: str = ""):
    """Log a prediction with structured format."""
    logger.info(
        f"Prediction made",
        extra={
            "request_id": request_id,
            "endpoint": endpoint,
            "prediction_class": prediction_class,
            "confidence": round(confidence, 4),
        }
    )
    
    # Also record in metrics
    metrics.prediction_classes[prediction_class] += 1
