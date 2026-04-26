"""Observability facade -- OTel is opt-in, not required.

When opentelemetry-api is importable, this module delegates to it.
When it is not installed, all objects returned are no-ops with zero runtime overhead.
"""

from __future__ import annotations

from typing import Any

try:
    from opentelemetry import metrics as _metrics, trace as _trace

    _HAS_OTEL = True
except ImportError:
    _HAS_OTEL = False


# --- No-op implementations ---


class _NoOpCounter:
    def add(self, amount: int | float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpHistogram:
    def record(self, amount: float, attributes: dict[str, Any] | None = None) -> None:
        pass


class _NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def __enter__(self) -> _NoOpSpan:
        return self

    def __exit__(self, *args: Any) -> None:
        pass


class _NoOpTracer:
    def start_as_current_span(self, name: str, **kwargs: Any) -> _NoOpSpan:
        return _NoOpSpan()


class _NoOpMeter:
    def create_counter(self, name: str, **kwargs: Any) -> _NoOpCounter:
        return _NoOpCounter()

    def create_histogram(self, name: str, **kwargs: Any) -> _NoOpHistogram:
        return _NoOpHistogram()


# --- Public API ---


def get_tracer(name: str) -> Any:
    """Get an OpenTelemetry Tracer, or a no-op if OTel is not installed."""
    if _HAS_OTEL:
        return _trace.get_tracer(name)
    return _NoOpTracer()


def get_meter(name: str) -> Any:
    """Get an OpenTelemetry Meter, or a no-op if OTel is not installed."""
    if _HAS_OTEL:
        return _metrics.get_meter(name)
    return _NoOpMeter()
