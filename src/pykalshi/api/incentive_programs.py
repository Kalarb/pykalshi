"""Incentive Programs API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import INCENTIVE_PROGRAMS_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_incentive_programs(
    client: KalshiHttpClient,
    *,
    status: Optional[str] = None,
    program_type: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Incentives.
    
    GET /trade-api/v2/incentive_programs
    
    List incentives with optional filters. Incentives are rewards programs for trading
activity on specific markets.
    """
    params = strip_none({
        "status": status,
        "type": program_type,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(INCENTIVE_PROGRAMS_URL, params=params)
