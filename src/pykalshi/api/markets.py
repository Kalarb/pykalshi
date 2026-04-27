"""Markets API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import MARKETS_URL, SERIES_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_market(client: KalshiHttpClient, ticker: str) -> dict[str, Any]:
    """Get Market.
    
    GET /trade-api/v2/markets/{ticker}
    
    Endpoint for getting data about a specific market by its ticker. A market represents a
specific binary outcome within an event that users can trade on (e.g., "Will candidate X
win?"). Markets have yes/no positions, current prices, volume, and settlement rules.
    """
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
    """Get Markets.
    
    GET /trade-api/v2/markets
    
    Filter by market status. Possible values: `unopened`, `open`, `closed`, `settled`. Leave
empty to return markets with any status. - Only one `status` filter may be supplied at a
time. - Timestamp filters will be mutually exclusive from other timestamp filters and
certain status filters.
    """
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
    client: KalshiHttpClient,
    ticker: str,
    *,
    depth: Optional[int] = None,
) -> dict[str, Any]:
    """Get Market Orderbook.
    
    GET /trade-api/v2/markets/{ticker}/orderbook
    
    Endpoint for getting the current order book for a specific market.  The order book shows
all active bid orders for both yes and no sides of a binary market. It returns yes bids
and no bids only (no asks are returned). This is because in binary markets, a bid for
yes at price X is equivalent to an ask for no at price (100-X). For example, a yes bid
at 7¢ is the same as a no ask at 93¢, with identical contract sizes.  Each side shows
price levels with their corresponding quantities and order counts, organized from best
to worst prices.
    """
    params = strip_none({"depth": depth})
    return await client.get(f"{MARKETS_URL}/{ticker}/orderbook", params=params)


async def get_trades(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    max_ts: Optional[int] = None,
    min_ts: Optional[int] = None,
) -> dict[str, Any]:
    """Get Trades.
    
    GET /trade-api/v2/markets/trades
    
    Endpoint for getting all trades for all markets. A trade represents a completed
transaction between two users on a specific market. Each trade includes the market
ticker, price, quantity, and timestamp information. This endpoint returns a paginated
response. Use the 'limit' parameter to control page size (1-1000, defaults to 100). The
response includes a 'cursor' field - pass this value in the 'cursor' parameter of your
next request to get the next page. An empty cursor indicates no more pages are
available.
    """
    params = strip_none({
        "ticker": ticker,
        "limit": limit,
        "cursor": cursor,
        "max_ts": max_ts,
        "min_ts": min_ts,
    })
    return await client.get(f"{MARKETS_URL}/trades", params=params)


async def get_market_orderbooks(
    client: KalshiHttpClient,
    tickers: list[str],
) -> dict[str, Any]:
    """Get Multiple Market Orderbooks.
    
    GET /trade-api/v2/markets/orderbooks
    
    Endpoint for getting the current order books for multiple markets in a single request.
The order book shows all active bid orders for both yes and no sides of a binary market.
It returns yes bids and no bids only (no asks are returned). This is because in binary
markets, a bid for yes at price X is equivalent to an ask for no at price (100-X). For
example, a yes bid at 7¢ is the same as a no ask at 93¢, with identical contract sizes.
Each side shows price levels with their corresponding quantities and order counts,
organized from best to worst prices. Returns one orderbook per requested market ticker.
    """
    return await client.get(
        f"{MARKETS_URL}/orderbooks", params={"tickers": ",".join(tickers)}
    )


async def get_market_candlesticks(
    client: KalshiHttpClient,
    series_ticker: str,
    ticker: str,
    *,
    start_ts: int,
    end_ts: int,
    period_interval: int,
    include_latest_before_start: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Market Candlesticks.
    
    GET /trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks
    
    Time period length of each candlestick in minutes. Valid values: 1 (1 minute), 60 (1
hour), 1440 (1 day). Candlesticks for markets that settled before the historical cutoff
are only available via `GET /historical/markets/{ticker}/candlesticks`. See [Historical
Data](https://kalshi.com/docs/getting_started/historical_data) for details.
    """
    params: dict[str, Any] = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "period_interval": period_interval,
    }
    if include_latest_before_start is not None:
        params["include_latest_before_start"] = include_latest_before_start
    return await client.get(
        f"{SERIES_URL}/{series_ticker}/markets/{ticker}/candlesticks",
        params=params,
    )
