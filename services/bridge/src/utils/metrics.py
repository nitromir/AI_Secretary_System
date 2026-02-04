"""Usage metrics tracking."""

import json
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

# Default metrics persistence file
DEFAULT_METRICS_FILE = Path.home() / ".cli-openai-bridge" / "metrics.json"


@dataclass
class RequestMetrics:
    """Metrics for a single request."""

    provider: str
    model: str
    stream: bool
    start_time: float
    end_time: float | None = None
    success: bool = False
    error: str | None = None
    tokens_estimate: int = 0

    @property
    def duration(self) -> float:
        """Request duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return 0.0


@dataclass
class ModelStats:
    """Aggregated stats for a specific model."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def avg_duration(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_duration / self.successful_requests

    @property
    def avg_tokens_per_request(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_tokens / self.successful_requests


@dataclass
class ProviderStats:
    """Aggregated stats for a provider."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_duration: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost_usd: float = 0.0
    errors: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    models: dict[str, ModelStats] = field(default_factory=lambda: defaultdict(ModelStats))

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def success_rate(self) -> float:
        """Success rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def avg_duration(self) -> float:
        """Average request duration."""
        if self.successful_requests == 0:
            return 0.0
        return self.total_duration / self.successful_requests

    @property
    def models_used(self) -> dict[str, int]:
        """Backward compatible: models with request counts."""
        return {name: stats.total_requests for name, stats in self.models.items()}


class MetricsCollector:
    """Collects and aggregates usage metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self._provider_stats: dict[str, ProviderStats] = defaultdict(ProviderStats)
        self._recent_requests: list[RequestMetrics] = []
        self._max_recent = 1000
        self._start_time = datetime.now()

    def record_request(
        self,
        provider: str,
        model: str,
        stream: bool,
        duration: float,
        success: bool,
        error: str | None = None,
        tokens: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost_usd: float = 0.0,
    ) -> None:
        """Record a completed request."""
        # For backward compatibility, if tokens is provided but not split
        if tokens > 0 and prompt_tokens == 0 and completion_tokens == 0:
            # Estimate split (rough: 30% prompt, 70% completion)
            prompt_tokens = int(tokens * 0.3)
            completion_tokens = tokens - prompt_tokens

        with self._lock:
            stats = self._provider_stats[provider]
            model_stats = stats.models[model]

            stats.total_requests += 1
            model_stats.total_requests += 1

            if success:
                stats.successful_requests += 1
                stats.total_duration += duration
                stats.prompt_tokens += prompt_tokens
                stats.completion_tokens += completion_tokens
                stats.total_cost_usd += cost_usd

                model_stats.successful_requests += 1
                model_stats.total_duration += duration
                model_stats.prompt_tokens += prompt_tokens
                model_stats.completion_tokens += completion_tokens
                model_stats.total_cost_usd += cost_usd
            else:
                stats.failed_requests += 1
                model_stats.failed_requests += 1
                if error:
                    # Categorize error
                    error_type = self._categorize_error(error)
                    stats.errors[error_type] += 1

            # Store recent request
            metrics = RequestMetrics(
                provider=provider,
                model=model,
                stream=stream,
                start_time=time.time() - duration,
                end_time=time.time(),
                success=success,
                error=error,
                tokens_estimate=prompt_tokens + completion_tokens,
            )
            self._recent_requests.append(metrics)

            # Trim old requests
            if len(self._recent_requests) > self._max_recent:
                self._recent_requests = self._recent_requests[-self._max_recent :]

    def _categorize_error(self, error: str) -> str:
        """Categorize error message."""
        error_lower = error.lower()
        if "timeout" in error_lower:
            return "timeout"
        if "connection" in error_lower:
            return "connection"
        if "not found" in error_lower:
            return "not_found"
        if "auth" in error_lower:
            return "authentication"
        return "other"

    def get_stats(self) -> dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            uptime = (datetime.now() - self._start_time).total_seconds()

            total_requests = sum(s.total_requests for s in self._provider_stats.values())
            total_success = sum(s.successful_requests for s in self._provider_stats.values())
            total_prompt = sum(s.prompt_tokens for s in self._provider_stats.values())
            total_completion = sum(s.completion_tokens for s in self._provider_stats.values())
            total_cost = sum(s.total_cost_usd for s in self._provider_stats.values())

            return {
                "uptime_seconds": uptime,
                "total_requests": total_requests,
                "total_successful": total_success,
                "total_failed": total_requests - total_success,
                "overall_success_rate": (total_success / total_requests * 100)
                if total_requests > 0
                else 0,
                "total_tokens": {
                    "prompt": total_prompt,
                    "completion": total_completion,
                    "total": total_prompt + total_completion,
                },
                "total_cost_usd": total_cost,
                "providers": {
                    name: {
                        "total_requests": stats.total_requests,
                        "successful_requests": stats.successful_requests,
                        "failed_requests": stats.failed_requests,
                        "success_rate": stats.success_rate,
                        "avg_duration_seconds": stats.avg_duration,
                        "tokens": {
                            "prompt": stats.prompt_tokens,
                            "completion": stats.completion_tokens,
                            "total": stats.total_tokens,
                        },
                        "cost_usd": stats.total_cost_usd,
                        "models": {
                            model_name: {
                                "total_requests": model_stats.total_requests,
                                "successful_requests": model_stats.successful_requests,
                                "failed_requests": model_stats.failed_requests,
                                "success_rate": model_stats.success_rate,
                                "avg_duration_seconds": model_stats.avg_duration,
                                "tokens": {
                                    "prompt": model_stats.prompt_tokens,
                                    "completion": model_stats.completion_tokens,
                                    "total": model_stats.total_tokens,
                                },
                                "avg_tokens_per_request": model_stats.avg_tokens_per_request,
                                "cost_usd": model_stats.total_cost_usd,
                            }
                            for model_name, model_stats in stats.models.items()
                        },
                        "models_used": dict(stats.models_used),  # Backward compatible
                        "errors": dict(stats.errors),
                    }
                    for name, stats in self._provider_stats.items()
                },
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._provider_stats.clear()
            self._recent_requests.clear()
            self._start_time = datetime.now()

    def save_to_file(self, filepath: Path | None = None) -> bool:
        """
        Save metrics to a JSON file for persistence across restarts.

        Args:
            filepath: Path to save to (default: ~/.cli-openai-bridge/metrics.json)

        Returns:
            True if saved successfully
        """
        filepath = filepath or DEFAULT_METRICS_FILE

        try:
            # Ensure directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with self._lock:
                data = {
                    "saved_at": datetime.now().isoformat(),
                    "start_time": self._start_time.isoformat(),
                    "providers": {},
                }

                for name, stats in self._provider_stats.items():
                    data["providers"][name] = {
                        "total_requests": stats.total_requests,
                        "successful_requests": stats.successful_requests,
                        "failed_requests": stats.failed_requests,
                        "total_duration": stats.total_duration,
                        "prompt_tokens": stats.prompt_tokens,
                        "completion_tokens": stats.completion_tokens,
                        "total_cost_usd": stats.total_cost_usd,
                        "errors": dict(stats.errors),
                        "models": {
                            model_name: {
                                "total_requests": model_stats.total_requests,
                                "successful_requests": model_stats.successful_requests,
                                "failed_requests": model_stats.failed_requests,
                                "total_duration": model_stats.total_duration,
                                "prompt_tokens": model_stats.prompt_tokens,
                                "completion_tokens": model_stats.completion_tokens,
                                "total_cost_usd": model_stats.total_cost_usd,
                            }
                            for model_name, model_stats in stats.models.items()
                        },
                    }

            filepath.write_text(json.dumps(data, indent=2))
            logger.info(f"Metrics saved to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to save metrics: {e}")
            return False

    def load_from_file(self, filepath: Path | None = None) -> bool:
        """
        Load metrics from a JSON file.

        Args:
            filepath: Path to load from (default: ~/.cli-openai-bridge/metrics.json)

        Returns:
            True if loaded successfully
        """
        filepath = filepath or DEFAULT_METRICS_FILE

        if not filepath.exists():
            logger.debug(f"No metrics file found at {filepath}")
            return False

        try:
            data = json.loads(filepath.read_text())

            with self._lock:
                for name, prov_data in data.get("providers", {}).items():
                    stats = self._provider_stats[name]
                    stats.total_requests = prov_data.get("total_requests", 0)
                    stats.successful_requests = prov_data.get("successful_requests", 0)
                    stats.failed_requests = prov_data.get("failed_requests", 0)
                    stats.total_duration = prov_data.get("total_duration", 0.0)
                    stats.prompt_tokens = prov_data.get("prompt_tokens", 0)
                    stats.completion_tokens = prov_data.get("completion_tokens", 0)
                    stats.total_cost_usd = prov_data.get("total_cost_usd", 0.0)

                    for err_type, count in prov_data.get("errors", {}).items():
                        stats.errors[err_type] = count

                    for model_name, model_data in prov_data.get("models", {}).items():
                        model_stats = stats.models[model_name]
                        model_stats.total_requests = model_data.get("total_requests", 0)
                        model_stats.successful_requests = model_data.get("successful_requests", 0)
                        model_stats.failed_requests = model_data.get("failed_requests", 0)
                        model_stats.total_duration = model_data.get("total_duration", 0.0)
                        model_stats.prompt_tokens = model_data.get("prompt_tokens", 0)
                        model_stats.completion_tokens = model_data.get("completion_tokens", 0)
                        model_stats.total_cost_usd = model_data.get("total_cost_usd", 0.0)

            logger.info(f"Metrics loaded from {filepath}")
            return True

        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            return False


# Global metrics collector instance
_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
