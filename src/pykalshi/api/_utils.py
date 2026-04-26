"""Shared utilities for API modules."""

from __future__ import annotations

from typing import Any


def strip_none(d: dict[str, Any]) -> dict[str, Any]:
    """Remove keys with None values from a dict."""
    return {k: v for k, v in d.items() if v is not None}


# Kalshi API base paths
EXCHANGE_URL = "/trade-api/v2/exchange"
MARKETS_URL = "/trade-api/v2/markets"
PORTFOLIO_URL = "/trade-api/v2/portfolio"
SERIES_URL = "/trade-api/v2/series"
EVENTS_URL = "/trade-api/v2/events"
ACCOUNT_URL = "/trade-api/v2/account"
SEARCH_URL = "/trade-api/v2/search"
