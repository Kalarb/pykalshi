"""Unit tests for _observability.py — no-op facade behavior."""

from __future__ import annotations

from pykalshi._observability import (
    _NoOpCounter,
    _NoOpHistogram,
    _NoOpMeter,
    _NoOpSpan,
    _NoOpTracer,
    get_meter,
    get_tracer,
)


class TestNoOpImplementations:
    def test_counter_add_does_not_raise(self) -> None:
        counter = _NoOpCounter()
        counter.add(1)
        counter.add(5, attributes={"key": "value"})

    def test_histogram_record_does_not_raise(self) -> None:
        hist = _NoOpHistogram()
        hist.record(0.5)
        hist.record(1.23, attributes={"key": "value"})

    def test_span_context_manager(self) -> None:
        span = _NoOpSpan()
        with span as s:
            assert s is span
            s.set_attribute("key", "value")

    def test_tracer_returns_span(self) -> None:
        tracer = _NoOpTracer()
        span = tracer.start_as_current_span("test")
        assert isinstance(span, _NoOpSpan)

    def test_meter_creates_counter(self) -> None:
        meter = _NoOpMeter()
        counter = meter.create_counter("test.counter")
        assert isinstance(counter, _NoOpCounter)

    def test_meter_creates_histogram(self) -> None:
        meter = _NoOpMeter()
        hist = meter.create_histogram("test.histogram")
        assert isinstance(hist, _NoOpHistogram)


class TestPublicApi:
    def test_get_tracer_returns_object(self) -> None:
        tracer = get_tracer("test")
        assert tracer is not None
        span = tracer.start_as_current_span("op")
        assert span is not None

    def test_get_meter_returns_object(self) -> None:
        meter = get_meter("test")
        assert meter is not None
        counter = meter.create_counter("c")
        counter.add(1)
        hist = meter.create_histogram("h")
        hist.record(0.5)
