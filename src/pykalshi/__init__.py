"""pykalshi — Shared async Python clients for the Kalshi prediction market API.

Pure 1:1 reflection of the Kalshi API. Each method maps to exactly one
API endpoint, one page at a time.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from .auth import KalshiCredentials
from .config import ClientConfig, Environment
from .exceptions import (
    KalshiAPIError,
    KalshiAuthError,
    KalshiError,
    KalshiRateLimitError,
    KalshiSequenceGapError,
    KalshiWebSocketError,
)
from .http_client import KalshiHttpClient
from .protocols import (
    KalshiHttpClientProtocol,
    KalshiWebSocketClientProtocol,
    RateLimiterProtocol,
)
from .rate_limiter import ReadWriteTokenBucket
from .ws_client import KalshiWebSocketClient
from ._version import __version__

__all__ = [
    # Core
    "KalshiCredentials",
    "ClientConfig",
    "Environment",
    # Clients
    "KalshiHttpClient",
    "KalshiWebSocketClient",
    # Rate limiter
    "ReadWriteTokenBucket",
    # Protocols (typed contract)
    "KalshiHttpClientProtocol",
    "KalshiWebSocketClientProtocol",
    "RateLimiterProtocol",
    # Exceptions
    "KalshiError",
    "KalshiAuthError",
    "KalshiAPIError",
    "KalshiRateLimitError",
    "KalshiWebSocketError",
    "KalshiSequenceGapError",
    # Convenience constructors
    "create_http_client",
    "create_ws_client",
    # Version
    "__version__",
]


def create_http_client(
    key_id: str,
    private_key_path: str,
    environment: Environment = Environment.DEMO,
    global_rate: float = 20.0,
    write_rate: float = 10.0,
    max_retries: int = 4,
    base_retry_delay: float = 0.1,
) -> KalshiHttpClient:
    """Drop-in replacement for the old KalshiHttpClient constructor."""
    return KalshiHttpClient(
        credentials=KalshiCredentials.from_key_file(key_id, private_key_path),
        config=ClientConfig(
            environment=environment,
            read_rate=global_rate,
            write_rate=write_rate,
            max_retries=max_retries,
            base_retry_delay=base_retry_delay,
        ),
    )


def create_ws_client(
    key_id: str,
    private_key_path: str,
    environment: Environment = Environment.DEMO,
    on_message_callback: Callable[[str], Awaitable[None]] | None = None,
) -> KalshiWebSocketClient:
    """Drop-in replacement for the old KalshiWebSocketClient constructor."""
    return KalshiWebSocketClient(
        credentials=KalshiCredentials.from_key_file(key_id, private_key_path),
        config=ClientConfig(environment=environment),
        on_message_callback=on_message_callback,
    )
