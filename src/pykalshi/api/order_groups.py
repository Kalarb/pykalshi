"""Order Groups API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import PORTFOLIO_URL, validate_path_param

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_order_groups(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Order Groups.
    
    GET /trade-api/v2/portfolio/order_groups
    
    Retrieves all order groups for the authenticated user.
    """
    return await client.get(f"{PORTFOLIO_URL}/order_groups")


async def create_order_group(
    client: KalshiHttpClient, contracts_limit: int
) -> dict[str, Any]:
    """Create Order Group.
    
    POST /trade-api/v2/portfolio/order_groups/create
    
    Creates a new order group with a contracts limit measured over a rolling 15-second
window. When the limit is hit, all orders in the group are cancelled and no new orders
can be placed until reset.
    """
    return await client.post(
        f"{PORTFOLIO_URL}/order_groups/create",
        body={"contracts_limit": contracts_limit},
    )


async def get_order_group(
    client: KalshiHttpClient, order_group_id: str
) -> dict[str, Any]:
    """Get Order Group.
    
    GET /trade-api/v2/portfolio/order_groups/{order_group_id}
    
    Retrieves details for a single order group including all order IDs and auto-cancel
status.
    """
    validate_path_param("order_group_id", order_group_id)
    return await client.get(f"{PORTFOLIO_URL}/order_groups/{order_group_id}")


async def delete_order_group(
    client: KalshiHttpClient, order_group_id: str
) -> dict[str, Any]:
    """Delete Order Group.

    DELETE /trade-api/v2/portfolio/order_groups/{order_group_id}

    Deletes an order group and cancels all orders within it. This permanently removes the
group.
    """
    validate_path_param("order_group_id", order_group_id)
    return await client.delete(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}", body={}
    )


async def reset_order_group(
    client: KalshiHttpClient, order_group_id: str
) -> dict[str, Any]:
    """Reset Order Group.

    PUT /trade-api/v2/portfolio/order_groups/{order_group_id}/reset

    Resets the order group's matched contracts counter to zero, allowing new orders to be
placed again after the limit was hit.
    """
    validate_path_param("order_group_id", order_group_id)
    return await client.put(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}/reset", body={}
    )


async def trigger_order_group(
    client: KalshiHttpClient,
    order_group_id: str,
    *,
    subaccount: Optional[int] = None,
) -> dict[str, Any]:
    """Trigger Order Group.
    
    PUT /trade-api/v2/portfolio/order_groups/{order_group_id}/trigger
    
    Triggers the order group, canceling all orders in the group and preventing new orders
until the group is reset.
    """
    params = {"subaccount": subaccount} if subaccount is not None else None
    return await client.put(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}/trigger",
        body={},
        params=params,
    )


async def update_order_group_limit(
    client: KalshiHttpClient,
    order_group_id: str,
    *,
    limit: int,
) -> dict[str, Any]:
    """Update Order Group Limit.
    
    PUT /trade-api/v2/portfolio/order_groups/{order_group_id}/limit
    
    Updates the order group contracts limit (rolling 15-second window). If the updated limit
would immediately trigger the group, all orders in the group are canceled and the group
is triggered.
    """
    return await client.put(
        f"{PORTFOLIO_URL}/order_groups/{order_group_id}/limit",
        body={"limit": limit},
    )
