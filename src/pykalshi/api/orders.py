"""Orders API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import PORTFOLIO_URL, strip_none, validate_path_param

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_orders(
    client: KalshiHttpClient,
    *,
    ticker: Optional[str] = None,
    event_ticker: Optional[str] = None,
    min_ts: Optional[int] = None,
    max_ts: Optional[int] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Get Orders.
    
    GET /trade-api/v2/portfolio/orders
    
    Restricts the response to orders that have a certain status: resting, canceled, or
executed. Orders that have been canceled or fully executed before the historical cutoff
are only available via `GET /historical/orders`. Resting orders will always be available
through this endpoint. See [Historical
Data](https://kalshi.com/docs/getting_started/historical_data) for details.
    """
    params = strip_none({
        "ticker": ticker,
        "event_ticker": event_ticker,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "status": status,
        "limit": limit,
        "cursor": cursor,
    })
    return await client.get(f"{PORTFOLIO_URL}/orders", params=params)


async def get_order(client: KalshiHttpClient, order_id: str) -> dict[str, Any]:
    """Get Order.

    GET /trade-api/v2/portfolio/orders/{order_id}

    Endpoint for getting a single order.
    """
    validate_path_param("order_id", order_id)
    return await client.get(f"{PORTFOLIO_URL}/orders/{order_id}")


async def create_order(
    client: KalshiHttpClient,
    *,
    ticker: str,
    side: str,
    action: str,
    count: Optional[int] = None,
    count_fp: Optional[str] = None,
    client_order_id: Optional[str] = None,
    order_type: Optional[str] = None,
    yes_price: Optional[int] = None,
    no_price: Optional[int] = None,
    yes_price_dollars: Optional[str] = None,
    no_price_dollars: Optional[str] = None,
    expiration_ts: Optional[int] = None,
    time_in_force: Optional[str] = None,
    buy_max_cost: Optional[int] = None,
    post_only: Optional[bool] = None,
    reduce_only: Optional[bool] = None,
    self_trade_prevention_type: Optional[str] = None,
    order_group_id: Optional[str] = None,
    cancel_order_on_pause: Optional[bool] = None,
) -> dict[str, Any]:
    """Create Order.
    
    POST /trade-api/v2/portfolio/orders
    
    Endpoint for submitting orders in a market. Each user is limited to 200 000 open orders
at a time.
    """
    payload = strip_none({
        "ticker": ticker,
        "side": side,
        "action": action,
        "count": count,
        "count_fp": count_fp,
        "client_order_id": client_order_id,
        "type": order_type,
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_price_dollars": yes_price_dollars,
        "no_price_dollars": no_price_dollars,
        "expiration_ts": expiration_ts,
        "time_in_force": time_in_force,
        "buy_max_cost": buy_max_cost,
        "post_only": post_only,
        "reduce_only": reduce_only,
        "self_trade_prevention_type": self_trade_prevention_type,
        "order_group_id": order_group_id,
        "cancel_order_on_pause": cancel_order_on_pause,
    })
    return await client.post(f"{PORTFOLIO_URL}/orders", body=payload)


async def cancel_order(client: KalshiHttpClient, order_id: str) -> dict[str, Any]:
    """Cancel Order.
    
    DELETE /trade-api/v2/portfolio/orders/{order_id}
    
    Endpoint for canceling orders. The value for the orderId should match the id field of
the order you want to decrease. Commonly, DELETE-type endpoints return 204 status with
no body content on success. But we can't completely delete the order, as it may be
partially filled already. Instead, the DeleteOrder endpoint reduce the order completely,
essentially zeroing the remaining resting contracts on it. The zeroed order is returned
on the response payload as a form of validation for the client.
    """
    validate_path_param("order_id", order_id)
    return await client.delete(f"{PORTFOLIO_URL}/orders/{order_id}", body={})


async def amend_order(
    client: KalshiHttpClient,
    order_id: str,
    *,
    ticker: str,
    side: str,
    action: str,
    client_order_id: str,
    updated_client_order_id: str,
    count: Optional[int] = None,
    count_fp: Optional[str] = None,
    yes_price: Optional[int] = None,
    no_price: Optional[int] = None,
    yes_price_dollars: Optional[str] = None,
    no_price_dollars: Optional[str] = None,
) -> dict[str, Any]:
    """Amend Order.
    
    POST /trade-api/v2/portfolio/orders/{order_id}/amend
    
    Endpoint for amending the max number of fillable contracts and/or price in an existing
order. Max fillable contracts is `remaining_count` + `fill_count`.
    """
    validate_path_param("order_id", order_id)
    payload = strip_none({
        "ticker": ticker,
        "side": side,
        "action": action,
        "client_order_id": client_order_id,
        "updated_client_order_id": updated_client_order_id,
        "count": count,
        "count_fp": count_fp,
        "yes_price": yes_price,
        "no_price": no_price,
        "yes_price_dollars": yes_price_dollars,
        "no_price_dollars": no_price_dollars,
    })
    return await client.post(f"{PORTFOLIO_URL}/orders/{order_id}/amend", body=payload)


async def decrease_order(
    client: KalshiHttpClient,
    order_id: str,
    *,
    reduce_by: Optional[int] = None,
    reduce_to: Optional[int] = None,
    reduce_by_fp: Optional[str] = None,
    reduce_to_fp: Optional[str] = None,
) -> dict[str, Any]:
    """Decrease Order.
    
    POST /trade-api/v2/portfolio/orders/{order_id}/decrease
    
    Endpoint for decreasing the number of contracts in an existing order. This is the only
kind of edit available on order quantity. Cancelling an order is equivalent to
decreasing an order amount to zero.
    """
    validate_path_param("order_id", order_id)
    payload = strip_none({
        "reduce_by": reduce_by,
        "reduce_to": reduce_to,
        "reduce_by_fp": reduce_by_fp,
        "reduce_to_fp": reduce_to_fp,
    })
    return await client.post(f"{PORTFOLIO_URL}/orders/{order_id}/decrease", body=payload)


async def get_queue_positions(
    client: KalshiHttpClient,
    *,
    market_tickers: Optional[str] = None,
    event_ticker: Optional[str] = None,
) -> dict[str, Any]:
    """Get Queue Positions for Orders.
    
    GET /trade-api/v2/portfolio/orders/queue_positions
    
    Endpoint for getting queue positions for all resting orders. Queue position represents
the number of contracts that need to be matched before an order receives a partial or
full match, determined using price-time priority.
    """
    params = strip_none({
        "market_tickers": market_tickers,
        "event_ticker": event_ticker,
    })
    return await client.get(f"{PORTFOLIO_URL}/orders/queue_positions", params=params)


async def get_order_queue_position(
    client: KalshiHttpClient, order_id: str
) -> dict[str, Any]:
    """Get Order Queue Position.
    
    GET /trade-api/v2/portfolio/orders/{order_id}/queue_position
    
    Endpoint for getting an order's queue position in the order book. This represents the
amount of orders that need to be matched before this order receives a partial or full
match. Queue position is determined using a price-time priority.
    """
    validate_path_param("order_id", order_id)
    return await client.get(f"{PORTFOLIO_URL}/orders/{order_id}/queue_position")


async def batch_create_orders(
    client: KalshiHttpClient,
    orders_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Batch Create Orders.
    
    POST /trade-api/v2/portfolio/orders/batched
    
    Endpoint for submitting a batch of orders. The maximum batch size scales with your
tier's write budget — see [Rate Limits and Tiers](/getting_started/rate_limits).
    """
    cleaned = [strip_none(order) for order in orders_list]
    return await client.post(f"{PORTFOLIO_URL}/orders/batched", body={"orders": cleaned})


async def batch_cancel_orders(
    client: KalshiHttpClient,
    order_ids: list[str],
) -> dict[str, Any]:
    """Batch Cancel Orders.
    
    DELETE /trade-api/v2/portfolio/orders/batched
    
    Endpoint for cancelling a batch of orders. The maximum batch size scales with your
tier's write budget — see [Rate Limits and Tiers](/getting_started/rate_limits).
    """
    return await client.delete(f"{PORTFOLIO_URL}/orders/batched", body={"ids": order_ids})
