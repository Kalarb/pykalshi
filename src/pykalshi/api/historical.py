"""Historical data API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from ._utils import HISTORICAL_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_cutoff(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/historical/cutoff"""
    return await client.get(f"{HISTORICAL_URL}/cutoff")


async def get_historical_markets(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    tickers: Optional[List[str]] = None,
    event_ticker: Optional[str] = None,
    series_ticker: Optional[str] = None,
    mve_filter: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/historical/markets"""
    params = strip_none({
        "limit": limit,
        "cursor": cursor,
        "tickers": ",".join(tickers) if tickers else None,
        "event_ticker": event_ticker,
        "series_ticker": series_ticker,
        "mve_filter": mve_filter,
    })
    return await client.get(f"{HISTORICAL_URL}/markets", params=params)


async def get_historical_market(
    client: KalshiHttpClient, ticker: str
) -> dict[str, Any]:
    """GET /trade-api/v2/historical/markets/{ticker}"""
    return await client.get(f"{HISTORICAL_URL}/markets/{ticker}")


async def get_historical_market_candlesticks(
    client: KalshiHttpClient,
    ticker: str,
    *,
    start_ts: int,
    end_ts: int,
    period_interval: int,
) -> dict[str, Any]:
    """GET /trade-api/v2/historical/markets/{ticker}/candlesticks"""
    params = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "period_interval": period_interval,
    }
    return await client.get(
        f"{HISTORICAL_URL}/markets/{ticker}/candlesticks", params=params
    )


async def get_historical_fills(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    max_ts: Optional[int] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/historical/fills"""
    params = strip_none({
        "ticker": ticker,
        "max_ts": max_ts,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{HISTORICAL_URL}/fills", params=params)


async def get_historical_orders(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    max_ts: Optional[int] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/historical/orders"""
    params = strip_none({
        "ticker": ticker,
        "max_ts": max_ts,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{HISTORICAL_URL}/orders", params=params)


async def get_historical_trades(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/historical/trades"""
    params = strip_none({
        "ticker": ticker,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{HISTORICAL_URL}/trades", params=params)
