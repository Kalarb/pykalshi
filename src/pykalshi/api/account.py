"""Account API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import ACCOUNT_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_api_limits(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Account API Limits.
    
    GET /trade-api/v2/account/limits
    
    Endpoint to retrieve the API tier limits associated with the authenticated user.
    """
    return await client.get(f"{ACCOUNT_URL}/limits")


async def get_endpoint_costs(client: KalshiHttpClient) -> dict[str, Any]:
    """List Non-Default Endpoint Costs.
    
    GET /trade-api/v2/account/endpoint_costs
    
    Lists API v2 endpoints whose configured token cost differs from the default cost.
Endpoints that use the default cost are omitted.
    """
    return await client.get(f"{ACCOUNT_URL}/endpoint_costs")
