"""Historical data API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import HISTORICAL_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_cutoff(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Historical Cutoff Timestamps.
    
    GET /trade-api/v2/historical/cutoff
    
    Returns the cutoff timestamps that define the boundary between **live** and
**historical** data.
    """
    return await client.get(f"{HISTORICAL_URL}/cutoff")


async def get_historical_markets(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    tickers: Optional[list[str]] = None,
    event_ticker: Optional[str] = None,
    series_ticker: Optional[str] = None,
    mve_filter: Optional[str] = None,
) -> dict[str, Any]:
    """Get Historical Markets.
    
    GET /trade-api/v2/historical/markets
    
    Endpoint for getting markets that have been archived to the historical database. Filters
are mutually exclusive.
    """
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
    """Get Historical Market.
    
    GET /trade-api/v2/historical/markets/{ticker}
    
    Endpoint for getting data about a specific market by its ticker from the historical
database.
    """
    return await client.get(f"{HISTORICAL_URL}/markets/{ticker}")


async def get_historical_market_candlesticks(
    client: KalshiHttpClient,
    ticker: str,
    *,
    start_ts: int,
    end_ts: int,
    period_interval: int,
) -> dict[str, Any]:
    """Get Historical Market Candlesticks.
    
    GET /trade-api/v2/historical/markets/{ticker}/candlesticks
    
    Endpoint for fetching historical candlestick data for markets that have been archived
from the live data set. Time period length of each candlestick in minutes. Valid values:
1 (1 minute), 60 (1 hour), 1440 (1 day).
    """
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
    """Get Historical Fills.
    
    GET /trade-api/v2/historical/fills
    
    Endpoint for getting all historical fills for the member. A fill is when a trade you
have is matched.
    """
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
    """Get Historical Orders.
    
    GET /trade-api/v2/historical/orders
    
    Endpoint for getting orders that have been archived to the historical database.
    """
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
    """Get Historical Trades.
    
    GET /trade-api/v2/historical/trades
    
    Endpoint for getting all historical trades for all markets. Trades that were filled
before the historical cutoff are available via this endpoint. See [Historical
Data](https://kalshi.com/docs/getting_started/historical_data) for details.
    """
    params = strip_none({
        "ticker": ticker,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{HISTORICAL_URL}/trades", params=params)
