"""Portfolio API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import PORTFOLIO_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_balance(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Balance.
    
    GET /trade-api/v2/portfolio/balance
    
    Endpoint for getting the balance and portfolio value of a member. Both values are
returned in cents.
    """
    return await client.get(f"{PORTFOLIO_URL}/balance")


async def get_positions(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    event_ticker: Optional[str] = None,
    count_filter: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Positions.
    
    GET /trade-api/v2/portfolio/positions
    
    Restricts the positions to those with any of following fields with non-zero values, as a
comma separated list. The following values are accepted: position, total_traded
    """
    params = strip_none({
        "ticker": ticker,
        "event_ticker": event_ticker,
        "count_filter": count_filter,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{PORTFOLIO_URL}/positions", params=params)


async def get_settlements(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Settlements.
    
    GET /trade-api/v2/portfolio/settlements
    
    Endpoint for getting the member's settlements historical track.
    """
    return await client.get(f"{PORTFOLIO_URL}/settlements")


async def get_fills(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Fills.

    GET /trade-api/v2/portfolio/fills

    Endpoint for getting all fills for the member. A fill is when a trade you have is
matched. Fills that occurred before the historical cutoff are only available via `GET
/historical/fills`. See [Historical
Data](https://kalshi.com/docs/getting_started/historical_data) for details.
    """
    return await client.get(f"{PORTFOLIO_URL}/fills")


async def get_deposits(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Deposits.

    GET /trade-api/v2/portfolio/deposits

    Retrieves the member's deposit history.
    """
    params = strip_none({"limit": limit, "cursor": cursor})
    return await client.get(f"{PORTFOLIO_URL}/deposits", params=params)


async def get_withdrawals(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Withdrawals.

    GET /trade-api/v2/portfolio/withdrawals

    Retrieves the member's withdrawal history.
    """
    params = strip_none({"limit": limit, "cursor": cursor})
    return await client.get(f"{PORTFOLIO_URL}/withdrawals", params=params)
