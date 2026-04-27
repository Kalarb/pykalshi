"""Structured Targets API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from ._utils import STRUCTURED_TARGETS_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_structured_targets(
    client: KalshiHttpClient,
    *,
    ids: Optional[List[str]] = None,
    target_type: Optional[str] = None,
    competition: Optional[str] = None,
    page_size: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Structured Targets.
    
    GET /trade-api/v2/structured_targets
    
    Page size (min: 1, max: 2000)
    """
    params = strip_none({
        "ids": ",".join(ids) if ids else None,
        "type": target_type,
        "competition": competition,
        "page_size": page_size,
        "cursor": cursor,
    })
    return await client.get(STRUCTURED_TARGETS_URL, params=params)


async def get_structured_target(
    client: KalshiHttpClient, structured_target_id: str
) -> dict[str, Any]:
    """Get Structured Target.
    
    GET /trade-api/v2/structured_targets/{structured_target_id}
    
    Endpoint for getting data about a specific structured target by its ID.
    """
    return await client.get(f"{STRUCTURED_TARGETS_URL}/{structured_target_id}")
