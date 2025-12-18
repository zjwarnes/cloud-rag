"""
Shared metrics collection and utilities.
"""

import logging
import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Single metric data point."""

    timestamp: str
    app_name: str
    query_id: str
    latency_ms: float
    success: bool
    error: Optional[str] = None


class MetricsCollector:
    """Collect metrics for an app."""

    def __init__(self, app_name: str, max_history: int = 1000):
        self.app_name = app_name
        self.metrics: deque = deque(maxlen=max_history)
        self.request_times: List[float] = []

    def record(
        self, query_id: str, latency_ms: float, success: bool = True, error: Optional[str] = None
    ) -> None:
        """Record a metric."""
        metric = Metric(
            timestamp=datetime.utcnow().isoformat(),
            app_name=self.app_name,
            query_id=query_id,
            latency_ms=latency_ms,
            success=success,
            error=error,
        )
        self.metrics.append(metric)
        self.request_times.append(latency_ms)

        # Log as JSON
        logger.info(json.dumps({"event": "request_completed", "metric": asdict(metric)}))

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregated statistics."""
        if not self.request_times:
            return {}

        times = sorted(self.request_times)
        return {
            "total_requests": len(times),
            "avg_latency_ms": sum(times) / len(times),
            "p50_latency_ms": times[len(times) // 2],
            "p99_latency_ms": times[int(len(times) * 0.99)] if len(times) > 1 else times[0],
            "min_latency_ms": min(times),
            "max_latency_ms": max(times),
            "error_count": sum(1 for m in self.metrics if not m.success),
        }

    def log_summary(self) -> None:
        """Log summary statistics."""
        stats = self.get_stats()
        if stats:
            logger.info(
                json.dumps({"event": "app_summary", "app_name": self.app_name, "stats": stats})
            )


# Global collector instances (one per app)
_collectors: Dict[str, MetricsCollector] = {}


def get_collector(app_name: str) -> MetricsCollector:
    """Get or create a metrics collector for an app."""
    if app_name not in _collectors:
        _collectors[app_name] = MetricsCollector(app_name)
    return _collectors[app_name]


class Timer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.elapsed_ms: float = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.elapsed_ms = (time.time() - self.start_time) * 1000
