"""Search API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import SEARCH_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_tags_by_categories(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Tags for Series Categories.
    
    GET /trade-api/v2/search/tags_by_categories
    
    Retrieve tags organized by series categories.
    """
    return await client.get(f"{SEARCH_URL}/tags_by_categories")


async def get_filters_by_sport(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Filters for Sports.
    
    GET /trade-api/v2/search/filters_by_sport
    
    Retrieve available filters organized by sport.
    """
    return await client.get(f"{SEARCH_URL}/filters_by_sport")
