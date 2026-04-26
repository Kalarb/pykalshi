"""Orders API methods."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ._utils import PORTFOLIO_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient

logger = logging.getLogger(__name__)


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
    """GET /trade-api/v2/portfolio/orders"""
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
    """GET /trade-api/v2/portfolio/orders/{order_id}"""
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
    """POST /trade-api/v2/portfolio/orders"""
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
    """DELETE /trade-api/v2/portfolio/orders/{order_id}"""
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
    """POST /trade-api/v2/portfolio/orders/{order_id}/amend"""
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
    """POST /trade-api/v2/portfolio/orders/{order_id}/decrease"""
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
    """GET /trade-api/v2/portfolio/orders/queue_positions"""
    params = strip_none({
        "market_tickers": market_tickers,
        "event_ticker": event_ticker,
    })
    return await client.get(f"{PORTFOLIO_URL}/orders/queue_positions", params=params)


async def get_order_queue_position(
    client: KalshiHttpClient, order_id: str
) -> dict[str, Any]:
    """GET /trade-api/v2/portfolio/orders/{order_id}/queue_position"""
    return await client.get(f"{PORTFOLIO_URL}/orders/{order_id}/queue_position")


async def batch_create_orders(
    client: KalshiHttpClient,
    orders_list: List[Dict[str, Any]],
) -> dict[str, Any]:
    """POST /trade-api/v2/portfolio/orders/batched

    Splits orders into groups based on write capacity and batch limit,
    executing groups sequentially and chunks within a group concurrently.
    """
    cleaned = [strip_none(order) for order in orders_list]
    if not cleaned:
        return {"orders": []}

    batch_limit = 20
    write_cap = int(client.limiter.write_capacity)
    cost_per_item = 1

    request_groups: List[List[List[Dict[str, Any]]]] = []
    concurrent_batches: List[List[Dict[str, Any]]] = []
    virtual_budget = max(write_cap, cost_per_item)

    idx = 0
    total = len(cleaned)

    while idx < total:
        if virtual_budget < cost_per_item:
            if concurrent_batches:
                request_groups.append(concurrent_batches)
                concurrent_batches = []
            virtual_budget = write_cap

        chunk_size = min(batch_limit, virtual_budget, total - idx)
        if chunk_size < 1:
            chunk_size = 1

        chunk = cleaned[idx : idx + chunk_size]
        concurrent_batches.append(chunk)

        virtual_budget -= len(chunk) * cost_per_item
        idx += len(chunk)

        if virtual_budget < cost_per_item:
            request_groups.append(concurrent_batches)
            concurrent_batches = []
            virtual_budget = write_cap

    if concurrent_batches:
        request_groups.append(concurrent_batches)

    final_results: List[Any] = []
    errors: List[Exception] = []

    async def _process_batch(chunk: List[Dict[str, Any]]) -> Any:
        try:
            return await client.post(
                f"{PORTFOLIO_URL}/orders/batched",
                body={"orders": chunk},
                write_cost=float(len(chunk)),
            )
        except Exception as e:
            return e

    for group in request_groups:
        results = await asyncio.gather(
            *[_process_batch(chunk) for chunk in group],
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Batch create failed: {res}")
                errors.append(res)
            elif isinstance(res, dict) and "orders" in res:
                final_results.extend(res["orders"])
            elif isinstance(res, list):
                final_results.extend(res)
            else:
                final_results.append(res)

    if not final_results and errors:
        raise errors[0]

    return {"orders": final_results}


async def batch_cancel_orders(
    client: KalshiHttpClient,
    order_ids: List[str],
) -> dict[str, Any]:
    """DELETE /trade-api/v2/portfolio/orders/batched

    Splits cancels into groups respecting write capacity.
    """
    if not order_ids:
        return {"orders": []}

    batch_limit = 20
    write_cap = int(client.limiter.write_capacity)
    cost_per_item = 0.2

    request_groups: List[List[List[str]]] = []
    concurrent_batches: List[List[str]] = []
    virtual_budget = float(max(write_cap, cost_per_item))

    idx = 0
    total = len(order_ids)

    while idx < total:
        if virtual_budget < (cost_per_item - 0.001):
            if concurrent_batches:
                request_groups.append(concurrent_batches)
                concurrent_batches = []
            virtual_budget = float(write_cap)

        max_items = int(virtual_budget / cost_per_item)
        chunk_size = min(batch_limit, max_items, total - idx)
        if chunk_size < 1:
            chunk_size = 1

        chunk = order_ids[idx : idx + chunk_size]
        concurrent_batches.append(chunk)

        virtual_budget -= len(chunk) * cost_per_item
        idx += len(chunk)

        if virtual_budget < (cost_per_item - 0.001):
            request_groups.append(concurrent_batches)
            concurrent_batches = []
            virtual_budget = float(write_cap)

    if concurrent_batches:
        request_groups.append(concurrent_batches)

    final_results: List[Any] = []
    errors: List[Exception] = []

    async def _process_batch(chunk: List[str]) -> Any:
        try:
            return await client.delete(
                f"{PORTFOLIO_URL}/orders/batched",
                body={"ids": chunk},
                write_cost=len(chunk) * cost_per_item,
            )
        except Exception as e:
            return e

    for group in request_groups:
        results = await asyncio.gather(
            *[_process_batch(chunk) for chunk in group],
            return_exceptions=True,
        )
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Batch cancel failed: {res}")
                errors.append(res)
            elif isinstance(res, dict) and "orders" in res:
                final_results.extend(res["orders"])
            elif isinstance(res, list):
                final_results.extend(res)
            else:
                final_results.append(res)

    if not final_results and errors:
        raise errors[0]

    return {"orders": final_results}
