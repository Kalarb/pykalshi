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
    """GET /trade-api/v2/series/{series_ticker}"""
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
) -> dict[str, Any]:
    """GET /trade-api/v2/series"""
    params = strip_none({
        "category": category,
        "tags": tags,
        "include_product_metadata": include_product_metadata,
        "include_volume": include_volume,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(SERIES_URL, params=params)
