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


async def get_event_candlesticks(
    client: KalshiHttpClient,
    series_ticker: str,
    event_ticker: str,
    *,
    start_ts: int,
    end_ts: int,
    period_interval: int,
) -> dict[str, Any]:
    """GET /trade-api/v2/series/{series_ticker}/events/{ticker}/candlesticks"""
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
    """GET /trade-api/v2/series/{s}/events/{t}/forecast_percentile_history"""
    params: dict[str, Any] = {
        "percentiles": ",".join(str(p) for p in percentiles),
        "start_ts": start_ts,
        "end_ts": end_ts,
        "period_interval": period_interval,
    }
    return await client.get(
        f"{SERIES_URL}/{series_ticker}/events/{event_ticker}/forecast_percentile_history",
        params=params,
    )
