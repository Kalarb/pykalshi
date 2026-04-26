"""Events API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import EVENTS_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_event(
    client: KalshiHttpClient,
    event_ticker: str,
    *,
    with_nested_markets: Optional[bool] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/events/{event_ticker}"""
    params = strip_none({"with_nested_markets": with_nested_markets})
    return await client.get(f"{EVENTS_URL}/{event_ticker}", params=params)


async def get_events(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    with_nested_markets: Optional[bool] = None,
    with_milestones: Optional[bool] = None,
    status: Optional[str] = None,
    series_ticker: Optional[str] = None,
    min_close_ts: Optional[int] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/events"""
    params = strip_none({
        "limit": limit,
        "cursor": cursor,
        "with_nested_markets": with_nested_markets,
        "with_milestones": with_milestones,
        "status": status,
        "series_ticker": series_ticker,
        "min_close_ts": min_close_ts,
    })
    return await client.get(EVENTS_URL, params=params)


async def get_multivariate_events(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    series_ticker: Optional[str] = None,
    collection_ticker: Optional[str] = None,
    with_nested_markets: Optional[bool] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/events/multivariate"""
    params = strip_none({
        "limit": limit,
        "cursor": cursor,
        "series_ticker": series_ticker,
        "collection_ticker": collection_ticker,
        "with_nested_markets": with_nested_markets,
    })
    return await client.get(f"{EVENTS_URL}/multivariate", params=params)


async def get_event_metadata(
    client: KalshiHttpClient, event_ticker: str
) -> dict[str, Any]:
    """GET /trade-api/v2/events/{event_ticker}/metadata"""
    return await client.get(f"{EVENTS_URL}/{event_ticker}/metadata")
