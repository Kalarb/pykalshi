"""Milestones API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import MILESTONES_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_milestone(
    client: KalshiHttpClient, milestone_id: str
) -> dict[str, Any]:
    """GET /trade-api/v2/milestones/{milestone_id}"""
    return await client.get(f"{MILESTONES_URL}/{milestone_id}")


async def get_milestones(
    client: KalshiHttpClient,
    *,
    limit: Optional[int] = None,
    minimum_start_date: Optional[str] = None,
    category: Optional[str] = None,
    competition: Optional[str] = None,
    source_id: Optional[str] = None,
    milestone_type: Optional[str] = None,
    related_event_ticker: Optional[str] = None,
    cursor: Optional[str] = None,
    min_updated_ts: Optional[int] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/milestones"""
    params = strip_none({
        "limit": limit,
        "minimum_start_date": minimum_start_date,
        "category": category,
        "competition": competition,
        "source_id": source_id,
        "type": milestone_type,
        "related_event_ticker": related_event_ticker,
        "cursor": cursor,
        "min_updated_ts": min_updated_ts,
    })
    return await client.get(MILESTONES_URL, params=params)
