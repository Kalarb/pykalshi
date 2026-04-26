"""Portfolio API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import PORTFOLIO_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_balance(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/balance"""
    return await client.get(f"{PORTFOLIO_URL}/balance")


async def get_positions(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    event_ticker: Optional[str] = None,
    count_filter: Optional[str] = None,
    limit: Optional[str] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/positions"""
    params = strip_none({
        "ticker": ticker,
        "event_ticker": event_ticker,
        "count_filter": count_filter,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{PORTFOLIO_URL}/positions", params=params)


async def get_settlements(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/settlements"""
    return await client.get(f"{PORTFOLIO_URL}/settlements")


async def get_fills(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/fills"""
    return await client.get(f"{PORTFOLIO_URL}/fills")
