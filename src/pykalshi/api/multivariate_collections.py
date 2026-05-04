"""Multivariate Event Collections API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import MULTIVARIATE_COLLECTIONS_URL, strip_none, validate_path_param

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_multivariate_event_collections(
    client: KalshiHttpClient,
    *,
    status: Optional[str] = None,
    associated_event_ticker: Optional[str] = None,
    series_ticker: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Multivariate Event Collections.

    GET /trade-api/v2/multivariate_event_collections

    List multivariate event collections.
    """
    params = strip_none({
        "status": status,
        "associated_event_ticker": associated_event_ticker,
        "series_ticker": series_ticker,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(MULTIVARIATE_COLLECTIONS_URL, params=params)


async def get_multivariate_event_collection(
    client: KalshiHttpClient,
    collection_ticker: str,
) -> dict[str, Any]:
    """Get Multivariate Event Collection.

    GET /trade-api/v2/multivariate_event_collections/{collection_ticker}

    Get a single multivariate event collection by ticker.
    """
    validate_path_param("collection_ticker", collection_ticker)
    return await client.get(
        f"{MULTIVARIATE_COLLECTIONS_URL}/{collection_ticker}"
    )


async def get_multivariate_event_collection_lookup_history(
    client: KalshiHttpClient,
    collection_ticker: str,
    *,
    lookback_seconds: int,
) -> dict[str, Any]:
    """Get Multivariate Event Collection Lookup History.

    GET /trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup

    Get lookup history for a multivariate event collection.
    """
    validate_path_param("collection_ticker", collection_ticker)
    return await client.get(
        f"{MULTIVARIATE_COLLECTIONS_URL}/{collection_ticker}/lookup",
        params={"lookback_seconds": lookback_seconds},
    )


async def create_market_in_multivariate_event_collection(
    client: KalshiHttpClient,
    collection_ticker: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create Market In Multivariate Event Collection.

    POST /trade-api/v2/multivariate_event_collections/{collection_ticker}

    Create a market in a multivariate event collection.
    """
    validate_path_param("collection_ticker", collection_ticker)
    return await client.post(
        f"{MULTIVARIATE_COLLECTIONS_URL}/{collection_ticker}",
        body=strip_none(kwargs),
    )


async def lookup_tickers_in_multivariate_event_collection(
    client: KalshiHttpClient,
    collection_ticker: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Lookup Tickers For Market In Multivariate Event Collection.

    PUT /trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup

    Lookup tickers for a market in a multivariate event collection.
    """
    validate_path_param("collection_ticker", collection_ticker)
    return await client.put(
        f"{MULTIVARIATE_COLLECTIONS_URL}/{collection_ticker}/lookup",
        body=strip_none(kwargs),
    )
