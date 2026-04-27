"""Series API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import SERIES_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_series(
    client: KalshiHttpClient,
    series_ticker: str,
    *,
    include_volume: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Series.
    
    GET /trade-api/v2/series/{series_ticker}
    
    Endpoint for getting data about a specific series by its ticker.  A series represents a
template for recurring events that follow the same format and rules (e.g., "Monthly Jobs
Report", "Weekly Initial Jobless Claims", "Daily Weather in NYC"). Series define the
structure, settlement sources, and metadata that will be applied to each recurring event
instance within that series.
    """
    params = strip_none({"include_volume": include_volume})
    return await client.get(f"{SERIES_URL}/{series_ticker}", params=params)


async def get_series_list(
    client: KalshiHttpClient,
    *,
    category: Optional[str] = None,
    tags: Optional[str] = None,
    include_product_metadata: Optional[bool] = None,
    include_volume: Optional[bool] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    min_updated_ts: Optional[int] = None,
) -> dict[str, Any]:
    """Get Series List.
    
    GET /trade-api/v2/series
    
    Endpoint for getting data about multiple series with specified filters.  A series
represents a template for recurring events that follow the same format and rules (e.g.,
"Monthly Jobs Report", "Weekly Initial Jobless Claims", "Daily Weather in NYC"). This
endpoint allows you to browse and discover available series templates by category.
    """
    params = strip_none({
        "category": category,
        "tags": tags,
        "include_product_metadata": include_product_metadata,
        "include_volume": include_volume,
        "limit": limit,
        "cursor": cursor,
        "min_updated_ts": min_updated_ts,
    })
    return await client.get(SERIES_URL, params=params)


async def get_fee_changes(
    client: KalshiHttpClient,
    *,
    series_ticker: Optional[str] = None,
    show_historical: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Series Fee Changes.
    
    GET /trade-api/v2/series/fee_changes
    """
    params = strip_none({
        "series_ticker": series_ticker,
        "show_historical": show_historical,
    })
    return await client.get(f"{SERIES_URL}/fee_changes", params=params)
