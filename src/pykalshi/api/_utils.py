"""Shared utilities for API modules."""

from __future__ import annotations

from typing import Any


def strip_none(d: dict[str, Any]) -> dict[str, Any]:
    """Remove keys with None values from a dict."""
    return {k: v for k, v in d.items() if v is not None}


def validate_path_param(name: str, value: str) -> None:
    """Validate that a path parameter is non-empty."""
    if not value:
        raise ValueError(f"Path parameter '{name}' must not be empty")


# Kalshi API base paths
EXCHANGE_URL = "/trade-api/v2/exchange"
MARKETS_URL = "/trade-api/v2/markets"
PORTFOLIO_URL = "/trade-api/v2/portfolio"
SERIES_URL = "/trade-api/v2/series"
EVENTS_URL = "/trade-api/v2/events"
ACCOUNT_URL = "/trade-api/v2/account"
SEARCH_URL = "/trade-api/v2/search"
HISTORICAL_URL = "/trade-api/v2/historical"
API_KEYS_URL = "/trade-api/v2/api_keys"
COMMUNICATIONS_URL = "/trade-api/v2/communications"
LIVE_DATA_URL = "/trade-api/v2/live_data"
MILESTONES_URL = "/trade-api/v2/milestones"
STRUCTURED_TARGETS_URL = "/trade-api/v2/structured_targets"
INCENTIVE_PROGRAMS_URL = "/trade-api/v2/incentive_programs"
MULTIVARIATE_COLLECTIONS_URL = "/trade-api/v2/multivariate_event_collections"
