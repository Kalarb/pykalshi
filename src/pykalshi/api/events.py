"""Events API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import EVENTS_URL, SERIES_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_event(
    client: KalshiHttpClient,
    event_ticker: str,
    *,
    with_nested_markets: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Event.
    
    GET /trade-api/v2/events/{event_ticker}
    
    Endpoint for getting data about an event by its ticker. An event represents a real-world
occurrence that can be traded on, such as an election, sports game, or economic
indicator release. Events contain one or more markets where users can place trades on
different outcomes. All events are accessible through this endpoint, even if their
associated markets are older than the historical cutoff.
    """
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
    min_updated_ts: Optional[int] = None,
) -> dict[str, Any]:
    """Get Events.
    
    GET /trade-api/v2/events
    
    Get all events. This endpoint excludes multivariate events. To retrieve multivariate
events, use the GET /events/multivariate endpoint. All events are accessible through
this endpoint, even if their associated markets are older than the historical cutoff.
    """
    params = strip_none({
        "limit": limit,
        "cursor": cursor,
        "with_nested_markets": with_nested_markets,
        "with_milestones": with_milestones,
        "status": status,
        "series_ticker": series_ticker,
        "min_close_ts": min_close_ts,
        "min_updated_ts": min_updated_ts,
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
    """Get Multivariate Events.
    
    GET /trade-api/v2/events/multivariate
    
    Retrieve multivariate (combo) events. These are dynamically created events from
multivariate event collections. Supports filtering by series and collection ticker.
    """
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
    """Get Event Metadata.
    
    GET /trade-api/v2/events/{event_ticker}/metadata
    
    Endpoint for getting metadata about an event by its ticker.  Returns only the metadata
information for an event.
    """
    return await client.get(f"{EVENTS_URL}/{event_ticker}/metadata")


async def get_event_candlesticks(
    client: KalshiHttpClient,
    series_ticker: str,
    event_ticker: str,
    *,
    start_ts: int,
    end_ts: int,
    period_interval: int,
) -> dict[str, Any]:
    """Get Event Candlesticks.
    
    GET /trade-api/v2/series/{series_ticker}/events/{ticker}/candlesticks
    
    End-point for returning aggregated data across all markets corresponding to an event.
    """
    params = {
        "start_ts": start_ts,
        "end_ts": end_ts,
        "period_interval": period_interval,
    }
    return await client.get(
        f"{SERIES_URL}/{series_ticker}/events/{event_ticker}/candlesticks",
        params=params,
    )


async def get_forecast_percentile_history(
    client: KalshiHttpClient,
    series_ticker: str,
    event_ticker: str,
    *,
    percentiles: list[int],
    start_ts: int,
    end_ts: int,
    period_interval: int,
) -> dict[str, Any]:
    """Get Event Forecast Percentile History.
    
    GET /trade-api/v2/series/{s}/events/{t}/forecast_percentile_history
    
    Endpoint for getting the historical raw and formatted forecast numbers for an event at
specific percentiles.
    """
    params: dict[str, Any] = {
        "percentiles": [str(p) for p in percentiles],
        "start_ts": start_ts,
        "end_ts": end_ts,
        "period_interval": period_interval,
    }
    return await client.get(
        f"{SERIES_URL}/{series_ticker}/events/{event_ticker}/forecast_percentile_history",
        params=params,
    )
