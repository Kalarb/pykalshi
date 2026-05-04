"""Event Orders API methods (V2 order endpoints)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import PORTFOLIO_URL, strip_none, validate_path_param

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def create_event_order(
    client: KalshiHttpClient,
    *,
    ticker: str,
    client_order_id: str,
    side: str,
    count: str,
    price: str,
    time_in_force: str,
    self_trade_prevention_type: str,
    expiration_time: Optional[int] = None,
    post_only: Optional[bool] = None,
    cancel_order_on_pause: Optional[bool] = None,
    reduce_only: Optional[bool] = None,
    subaccount: Optional[int] = None,
    order_group_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create Order (V2).

    POST /trade-api/v2/portfolio/events/orders

    Submit an order using the V2 single-book model (bid/ask sides).
    """
    payload = strip_none({
        "ticker": ticker,
        "client_order_id": client_order_id,
        "side": side,
        "count": count,
        "price": price,
        "time_in_force": time_in_force,
        "self_trade_prevention_type": self_trade_prevention_type,
        "expiration_time": expiration_time,
        "post_only": post_only,
        "cancel_order_on_pause": cancel_order_on_pause,
        "reduce_only": reduce_only,
        "subaccount": subaccount,
        "order_group_id": order_group_id,
    })
    return await client.post(f"{PORTFOLIO_URL}/events/orders", body=payload)


async def cancel_event_order(
    client: KalshiHttpClient, order_id: str
) -> dict[str, Any]:
    """Cancel Order (V2).

    DELETE /trade-api/v2/portfolio/events/orders/{order_id}

    Cancel an order using the V2 endpoint.
    """
    validate_path_param("order_id", order_id)
    return await client.delete(f"{PORTFOLIO_URL}/events/orders/{order_id}", body={})


async def amend_event_order(
    client: KalshiHttpClient,
    order_id: str,
    *,
    ticker: str,
    side: str,
    price: str,
    count: str,
    client_order_id: Optional[str] = None,
    updated_client_order_id: Optional[str] = None,
) -> dict[str, Any]:
    """Amend Order (V2).

    POST /trade-api/v2/portfolio/events/orders/{order_id}/amend

    Amend an order using the V2 single-book model.
    """
    validate_path_param("order_id", order_id)
    payload = strip_none({
        "ticker": ticker,
        "side": side,
        "price": price,
        "count": count,
        "client_order_id": client_order_id,
        "updated_client_order_id": updated_client_order_id,
    })
    return await client.post(
        f"{PORTFOLIO_URL}/events/orders/{order_id}/amend", body=payload
    )


async def decrease_event_order(
    client: KalshiHttpClient,
    order_id: str,
    *,
    reduce_to: str,
) -> dict[str, Any]:
    """Decrease Order (V2).

    POST /trade-api/v2/portfolio/events/orders/{order_id}/decrease

    Decrease an order using the V2 endpoint.
    """
    validate_path_param("order_id", order_id)
    return await client.post(
        f"{PORTFOLIO_URL}/events/orders/{order_id}/decrease",
        body={"reduce_to": reduce_to},
    )


async def batch_create_event_orders(
    client: KalshiHttpClient,
    orders_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Batch Create Orders (V2).

    POST /trade-api/v2/portfolio/events/orders/batched

    Submit a batch of orders using the V2 single-book model.
    """
    cleaned = [strip_none(order) for order in orders_list]
    return await client.post(
        f"{PORTFOLIO_URL}/events/orders/batched", body={"orders": cleaned}
    )


async def batch_cancel_event_orders(
    client: KalshiHttpClient,
    orders_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Batch Cancel Orders (V2).

    DELETE /trade-api/v2/portfolio/events/orders/batched

    Cancel a batch of orders using the V2 endpoint.
    """
    return await client.delete(
        f"{PORTFOLIO_URL}/events/orders/batched", body={"orders": orders_list}
    )
