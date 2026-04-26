"""Environment and client configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"


_ENV_URLS: dict[Environment, dict[str, str]] = {
    Environment.DEMO: {
        "http": "https://demo-api.kalshi.co",
        "ws": "wss://demo-api.kalshi.co",
    },
    Environment.PROD: {
        "http": "https://api.elections.kalshi.com",
        "ws": "wss://api.elections.kalshi.com",
    },
}


@dataclass(frozen=True)
class ClientConfig:
    """Immutable configuration for Kalshi clients.

    URL resolution precedence: explicit arg > env var > environment-derived default.
    """

    environment: Environment = Environment.DEMO
    http_base_url: Optional[str] = None
    ws_base_url: Optional[str] = None
    read_rate: float = 20.0
    write_rate: float = 10.0
    max_retries: int = 4
    base_retry_delay: float = 0.1
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    write_timeout: float = 10.0
    pool_timeout: float = 5.0

    @property
    def resolved_http_url(self) -> str:
        if self.http_base_url:
            return self.http_base_url
        from_env = os.environ.get("KALSHI_HTTP_BASE_URL")
        if from_env:
            return from_env
        return _ENV_URLS[self.environment]["http"]

    @property
    def resolved_ws_url(self) -> str:
        if self.ws_base_url:
            return self.ws_base_url
        from_env = os.environ.get("KALSHI_WS_BASE_URL")
        if from_env:
            return from_env
        return _ENV_URLS[self.environment]["ws"]
