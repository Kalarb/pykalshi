"""Unit tests for exceptions.py — construction and hierarchy."""

from __future__ import annotations

from pykalshi.exceptions import (
    KalshiAPIError,
    KalshiAuthError,
    KalshiError,
    KalshiRateLimitError,
    KalshiSequenceGapError,
    KalshiWebSocketError,
)


class TestExceptionHierarchy:
    def test_base_hierarchy(self) -> None:
        assert issubclass(KalshiAuthError, KalshiError)
        assert issubclass(KalshiAPIError, KalshiError)
        assert issubclass(KalshiRateLimitError, KalshiAPIError)
        assert issubclass(KalshiWebSocketError, KalshiError)
        assert issubclass(KalshiSequenceGapError, KalshiWebSocketError)

    def test_all_inherit_from_exception(self) -> None:
        for cls in (KalshiError, KalshiAuthError, KalshiAPIError,
                    KalshiRateLimitError, KalshiWebSocketError, KalshiSequenceGapError):
            assert issubclass(cls, Exception)


class TestKalshiAPIError:
    def test_construction(self) -> None:
        err = KalshiAPIError(status_code=404, body="not found", method="GET", path="/test")
        assert err.status_code == 404
        assert err.body == "not found"
        assert err.method == "GET"
        assert err.path == "/test"

    def test_message_format(self) -> None:
        err = KalshiAPIError(status_code=500, body="oops", method="POST", path="/api")
        assert "500" in str(err)
        assert "POST" in str(err)
        assert "/api" in str(err)

    def test_catchable_as_kalshi_error(self) -> None:
        try:
            raise KalshiAPIError(status_code=400, body="bad", method="GET", path="/x")
        except KalshiError as e:
            assert isinstance(e, KalshiAPIError)


class TestKalshiRateLimitError:
    def test_inherits_api_error(self) -> None:
        err = KalshiRateLimitError(status_code=429, body="slow down", method="POST", path="/orders")
        assert err.status_code == 429
        assert isinstance(err, KalshiAPIError)


class TestKalshiSequenceGapError:
    def test_construction(self) -> None:
        err = KalshiSequenceGapError(channel="orderbook_delta", expected=5, got=8)
        assert err.channel == "orderbook_delta"
        assert err.expected == 5
        assert err.got == 8

    def test_message_format(self) -> None:
        err = KalshiSequenceGapError(channel="ticker", expected=10, got=15)
        assert "ticker" in str(err)
        assert "10" in str(err)
        assert "15" in str(err)
