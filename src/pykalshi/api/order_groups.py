"""Order Groups API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import PORTFOLIO_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_order_groups(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/order_groups"""
    return await client.get(f"{PORTFOLIO_URL}/order_groups")


async def create_order_group(
    client: KalshiHttpClient, contracts_limit: int
) -> dict[str, Any]:
    """POST /trade-api/v2/portfolio/order_groups/create"""
    return await client.post(
        f"{PORTFOLIO_URL}/order_groups/create",
        body={"contracts_limit": contracts_limit},
    )


async def get_order_group(
    client: KalshiHttpClient, order_group_id: str
) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/order_groups/{order_group_id}"""
    return await client.get(f"{PORTFOLIO_URL}/order_groups/{order_group_id}")


async def delete_order_group(
    client: KalshiHttpClient, order_group_id: str
) -> dict[str, Any]:
    """DELETE /trade-api/v2/portfolio/order_groups/{order_group_id}"""
    return await client.delete(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}", body={}
    )


async def reset_order_group(
    client: KalshiHttpClient, order_group_id: str
) -> dict[str, Any]:
    """PUT /trade-api/v2/portfolio/order_groups/{order_group_id}/reset"""
    return await client.put(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}/reset", body={}
    )


async def trigger_order_group(
    client: KalshiHttpClient,
    order_group_id: str,
    *,
    subaccount: Optional[int] = None,
) -> dict[str, Any]:
    """PUT /trade-api/v2/portfolio/order_groups/{order_group_id}/trigger"""
    path = f"{PORTFOLIO_URL}/order_groups/{order_group_id}/trigger"
    if subaccount is not None:
        path += f"?subaccount={subaccount}"
    return await client.put(path, body={})


async def update_order_group_limit(
    client: KalshiHttpClient,
    order_group_id: str,
    *,
    limit: int,
) -> dict[str, Any]:
    """PUT /trade-api/v2/portfolio/order_groups/{order_group_id}/limit"""
    return await client.put(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}/limit",
        body={"limit": limit},
    )
