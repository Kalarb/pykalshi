"""Custom exception hierarchy for pykalshi."""

from __future__ import annotations


class KalshiError(Exception):
    """Base exception for all pykalshi errors."""


class KalshiAuthError(KalshiError):
    """RSA key loading or signing failure."""


class KalshiAPIError(KalshiError):
    """HTTP API returned an error status code."""

    def __init__(
        self,
        status_code: int,
        body: str,
        method: str,
        path: str,
    ) -> None:
        self.status_code = status_code
        self.body = body
        self.method = method
        self.path = path
        super().__init__(
            f"Kalshi API Error [{status_code}] {method} {path}: {body}"
        )


class KalshiRateLimitError(KalshiAPIError):
    """429 after all retries exhausted."""


class KalshiWebSocketError(KalshiError):
    """WebSocket connection or protocol error."""


class KalshiSequenceGapError(KalshiWebSocketError):
    """Detected a gap in the WS message sequence."""

    def __init__(self, channel: str, expected: int, got: int) -> None:
        self.channel = channel
        self.expected = expected
        self.got = got
        super().__init__(
            f"Sequence gap on {channel}: expected {expected}, got {got}"
        )
