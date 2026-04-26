"""Markets API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import MARKETS_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_market(client: KalshiHttpClient, ticker: str) -> dict[str, Any]:
    """GET /trade-api/v2/markets/{ticker}"""
    return await client.get(f"{MARKETS_URL}/{ticker}")


async def get_markets(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    event_ticker: Optional[str] = None,
    series_ticker: Optional[str] = None,
    min_created_ts: Optional[int] = None,
    max_created_ts: Optional[int] = None,
    max_close_ts: Optional[int] = None,
    min_close_ts: Optional[int] = None,
    min_settled_ts: Optional[int] = None,
    max_settled_ts: Optional[int] = None,
    status: Optional[str] = None,
    tickers: Optional[str] = None,
    mve_filter: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/markets"""
    params = strip_none({
        "limit": limit,
        "cursor": cursor,
        "event_ticker": event_ticker,
        "series_ticker": series_ticker,
        "min_created_ts": min_created_ts,
        "max_created_ts": max_created_ts,
        "max_close_ts": max_close_ts,
        "min_close_ts": min_close_ts,
        "min_settled_ts": min_settled_ts,
        "max_settled_ts": max_settled_ts,
        "status": status,
        "tickers": tickers,
        "mve_filter": mve_filter,
    })
    return await client.get(MARKETS_URL, params=params)


async def get_market_orderbook(
    client: KalshiHttpClient, ticker: str
) -> dict[str, Any]:
    """GET /trade-api/v2/markets/{ticker}/orderbook"""
    return await client.get(f"{MARKETS_URL}/{ticker}/orderbook")


async def get_trades(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    max_ts: Optional[int] = None,
    min_ts: Optional[int] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/markets/trades"""
    params = strip_none({
        "ticker": ticker,
        "limit": limit,
        "cursor": cursor,
        "max_ts": max_ts,
        "min_ts": min_ts,
    })
    return await client.get(f"{MARKETS_URL}/trades", params=params)
