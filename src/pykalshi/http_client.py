"""Async HTTP client for the Kalshi API."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from .auth import KalshiCredentials
from .config import ClientConfig
from .exceptions import KalshiAPIError, KalshiRateLimitError
from .rate_limiter import ReadWriteTokenBucket
from ._observability import get_meter, get_tracer
from .api import (
    account,
    api_keys,
    communications,
    events,
    exchange,
    historical,
    incentive_programs,
    live_data,
    markets,
    milestones,
    order_groups,
    orders,
    portfolio,
    search,
    series,
    structured_targets,
)

logger = logging.getLogger(__name__)


class KalshiHttpClient:
    """Async HTTP client with rate limiting, retry, and optional OTel."""

    def __init__(
        self,
        credentials: KalshiCredentials,
        config: ClientConfig = ClientConfig(),
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        rate_limiter: Optional[ReadWriteTokenBucket] = None,
    ) -> None:
        self._credentials = credentials
        self._config = config
        self._limiter = rate_limiter or ReadWriteTokenBucket(
            read_rate=config.read_rate,
            write_rate=config.write_rate,
        )

        client_kwargs: Dict[str, Any] = {
            "base_url": config.resolved_http_url,
            "timeout": httpx.Timeout(
                connect=config.connect_timeout,
                read=config.read_timeout,
                write=config.write_timeout,
                pool=config.pool_timeout,
            ),
        }
        if transport is not None:
            client_kwargs["transport"] = transport

        self._client = httpx.AsyncClient(**client_kwargs)

        self._tracer = get_tracer("pykalshi.http")
        self._meter = get_meter("pykalshi.http")
        self._orders_created = self._meter.create_counter(
            "pykalshi.orders.created_total",
            description="Total orders submitted",
        )
        self._orders_cancelled = self._meter.create_counter(
            "pykalshi.orders.cancelled_total",
            description="Total orders cancelled",
        )
        self._retries_429 = self._meter.create_counter(
            "pykalshi.http.retries_429_total",
            description="Total 429 retries",
        )
        self._rate_limiter_wait = self._meter.create_histogram(
            "pykalshi.rate_limiter.wait_duration",
            description="Time spent waiting on rate limiter (seconds)",
        )

    @property
    def limiter(self) -> ReadWriteTokenBucket:
        return self._limiter

    async def __aenter__(self) -> KalshiHttpClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    # --- Core request engine ---

    async def _execute_request(
        self,
        method: str,
        path: str,
        global_cost: float,
        write_cost: float,
        **kwargs: Any,
    ) -> Any:
        """Execute request with rate limiting and 429 retry."""
        wait_start = time.monotonic()
        await self._limiter.acquire(global_cost=global_cost, write_cost=write_cost)
        waited = time.monotonic() - wait_start
        if waited > 0.001:
            self._rate_limiter_wait.record(waited)

        headers = {**self._credentials.auth_headers(method, path), **kwargs.pop("headers", {})}
        kwargs["headers"] = headers

        retries = 0
        while True:
            try:
                response = await self._client.request(method, path, **kwargs)

                if response.status_code == 429:
                    if retries >= self._config.max_retries:
                        raise KalshiRateLimitError(
                            status_code=429,
                            body=response.text,
                            method=method,
                            path=path,
                        )
                    self._retries_429.add(1)
                    wait_time = self._config.base_retry_delay * (2 ** retries)
                    logger.warning(
                        "429 hit. Retrying in %.2fs (%d/%d)",
                        wait_time,
                        retries + 1,
                        self._config.max_retries,
                    )
                    await asyncio.sleep(wait_time)
                    retries += 1
                    continue

                if response.is_error:
                    raise KalshiAPIError(
                        status_code=response.status_code,
                        body=response.text,
                        method=method,
                        path=path,
                    )
                if not response.content:
                    return {}
                return response.json()

            except httpx.RequestError as e:
                if retries >= self._config.max_retries:
                    logger.error("Network error after %d retries: %s", retries, e)
                    raise
                wait_time = self._config.base_retry_delay * (2 ** retries)
                logger.warning(
                    "Network error: %s. Retrying in %.2fs (%d/%d)",
                    e,
                    wait_time,
                    retries + 1,
                    self._config.max_retries,
                )
                await asyncio.sleep(wait_time)
                retries += 1

    # --- HTTP verbs ---

    async def get(
        self, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        return await self._execute_request(
            "GET", path, 1.0, 0.0, params=params or {}
        )

    async def post(
        self, path: str, body: dict[str, Any], write_cost: float = 1.0
    ) -> Any:
        return await self._execute_request(
            "POST", path, 1.0, write_cost, json=body
        )

    async def put(
        self,
        path: str,
        body: dict[str, Any],
        write_cost: float = 1.0,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return await self._execute_request(
            "PUT", path, 1.0, write_cost, json=body, **({"params": params} if params else {})
        )

    async def delete(
        self,
        path: str,
        body: Optional[dict[str, Any]] = None,
        write_cost: float = 1.0,
    ) -> Any:
        return await self._execute_request(
            "DELETE", path, 1.0, write_cost, json=body or {}
        )

    # --- Exchange ---

    async def get_exchange_status(self) -> dict[str, Any]:
        return await exchange.get_exchange_status(self)

    async def get_exchange_schedule(self) -> dict[str, Any]:
        return await exchange.get_exchange_schedule(self)

    # --- Account ---

    async def get_api_limits(self) -> dict[str, Any]:
        return await account.get_api_limits(self)

    # --- Orders ---

    async def get_orders(self, **kwargs: Any) -> dict[str, Any]:
        return await orders.get_orders(self, **kwargs)

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await orders.get_order(self, order_id)

    async def create_order(self, **kwargs: Any) -> dict[str, Any]:
        return await orders.create_order(self, **kwargs)

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        return await orders.cancel_order(self, order_id)

    async def amend_order(self, order_id: str, **kwargs: Any) -> dict[str, Any]:
        return await orders.amend_order(self, order_id, **kwargs)

    async def decrease_order(self, order_id: str, **kwargs: Any) -> dict[str, Any]:
        return await orders.decrease_order(self, order_id, **kwargs)

    async def batch_create_orders(
        self, orders_list: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return await orders.batch_create_orders(self, orders_list)

    async def batch_cancel_orders(self, order_ids: list[str]) -> dict[str, Any]:
        return await orders.batch_cancel_orders(self, order_ids)

    async def get_queue_positions(self, **kwargs: Any) -> dict[str, Any]:
        return await orders.get_queue_positions(self, **kwargs)

    async def get_order_queue_position(self, order_id: str) -> dict[str, Any]:
        return await orders.get_order_queue_position(self, order_id)

    # --- Order Groups ---

    async def get_order_groups(self) -> dict[str, Any]:
        return await order_groups.get_order_groups(self)

    async def create_order_group(self, contracts_limit: int) -> dict[str, Any]:
        return await order_groups.create_order_group(self, contracts_limit)

    async def get_order_group(self, order_group_id: str) -> dict[str, Any]:
        return await order_groups.get_order_group(self, order_group_id)

    async def delete_order_group(self, order_group_id: str) -> dict[str, Any]:
        return await order_groups.delete_order_group(self, order_group_id)

    async def reset_order_group(self, order_group_id: str) -> dict[str, Any]:
        return await order_groups.reset_order_group(self, order_group_id)

    # --- Portfolio ---

    async def get_balance(self) -> dict[str, Any]:
        return await portfolio.get_balance(self)

    async def get_positions(self, **kwargs: Any) -> dict[str, Any]:
        return await portfolio.get_positions(self, **kwargs)

    async def get_settlements(self) -> dict[str, Any]:
        return await portfolio.get_settlements(self)

    async def get_fills(self) -> dict[str, Any]:
        return await portfolio.get_fills(self)

    # --- Markets ---

    async def get_market(self, ticker: str) -> dict[str, Any]:
        return await markets.get_market(self, ticker)

    async def get_markets(self, **kwargs: Any) -> dict[str, Any]:
        return await markets.get_markets(self, **kwargs)

    async def get_market_orderbook(self, ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await markets.get_market_orderbook(self, ticker, **kwargs)

    async def get_trades(self, **kwargs: Any) -> dict[str, Any]:
        return await markets.get_trades(self, **kwargs)

    # --- Events ---

    async def get_event(self, event_ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await events.get_event(self, event_ticker, **kwargs)

    async def get_events(self, **kwargs: Any) -> dict[str, Any]:
        return await events.get_events(self, **kwargs)

    async def get_multivariate_events(self, **kwargs: Any) -> dict[str, Any]:
        return await events.get_multivariate_events(self, **kwargs)

    async def get_event_metadata(self, event_ticker: str) -> dict[str, Any]:
        return await events.get_event_metadata(self, event_ticker)

    # --- Series ---

    async def get_series(self, series_ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await series.get_series(self, series_ticker, **kwargs)

    async def get_series_list(self, **kwargs: Any) -> dict[str, Any]:
        return await series.get_series_list(self, **kwargs)

    # --- Search ---

    async def get_tags_by_categories(self) -> dict[str, Any]:
        return await search.get_tags_by_categories(self)

    async def get_filters_by_sport(self) -> dict[str, Any]:
        return await search.get_filters_by_sport(self)

    # --- Exchange (additional) ---

    async def get_exchange_announcements(self) -> dict[str, Any]:
        return await exchange.get_exchange_announcements(self)

    async def get_user_data_timestamp(self) -> dict[str, Any]:
        return await exchange.get_user_data_timestamp(self)

    # --- Account (additional) ---

    async def get_endpoint_costs(self) -> dict[str, Any]:
        return await account.get_endpoint_costs(self)

    # --- Order Groups (additional) ---

    async def trigger_order_group(self, order_group_id: str, **kwargs: Any) -> dict[str, Any]:
        return await order_groups.trigger_order_group(self, order_group_id, **kwargs)

    async def update_order_group_limit(self, order_group_id: str, **kwargs: Any) -> dict[str, Any]:
        return await order_groups.update_order_group_limit(self, order_group_id, **kwargs)

    # --- Markets (additional) ---

    async def get_market_orderbooks(self, tickers: list[str]) -> dict[str, Any]:
        return await markets.get_market_orderbooks(self, tickers)

    async def get_market_candlesticks(self, series_ticker: str, ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await markets.get_market_candlesticks(self, series_ticker, ticker, **kwargs)

    # --- Events (additional) ---

    async def get_event_candlesticks(self, series_ticker: str, event_ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await events.get_event_candlesticks(self, series_ticker, event_ticker, **kwargs)

    async def get_forecast_percentile_history(self, series_ticker: str, event_ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await events.get_forecast_percentile_history(self, series_ticker, event_ticker, **kwargs)

    # --- Series (additional) ---

    async def get_fee_changes(self, **kwargs: Any) -> dict[str, Any]:
        return await series.get_fee_changes(self, **kwargs)

    # --- Historical ---

    async def get_historical_cutoff(self) -> dict[str, Any]:
        return await historical.get_cutoff(self)

    async def get_historical_markets(self, **kwargs: Any) -> dict[str, Any]:
        return await historical.get_historical_markets(self, **kwargs)

    async def get_historical_market(self, ticker: str) -> dict[str, Any]:
        return await historical.get_historical_market(self, ticker)

    async def get_historical_market_candlesticks(self, ticker: str, **kwargs: Any) -> dict[str, Any]:
        return await historical.get_historical_market_candlesticks(self, ticker, **kwargs)

    async def get_historical_fills(self, **kwargs: Any) -> dict[str, Any]:
        return await historical.get_historical_fills(self, **kwargs)

    async def get_historical_orders(self, **kwargs: Any) -> dict[str, Any]:
        return await historical.get_historical_orders(self, **kwargs)

    async def get_historical_trades(self, **kwargs: Any) -> dict[str, Any]:
        return await historical.get_historical_trades(self, **kwargs)

    # --- API Keys ---

    async def get_api_keys(self) -> dict[str, Any]:
        return await api_keys.get_api_keys(self)

    async def create_api_key(self, **kwargs: Any) -> dict[str, Any]:
        return await api_keys.create_api_key(self, **kwargs)

    async def generate_api_key(self, **kwargs: Any) -> dict[str, Any]:
        return await api_keys.generate_api_key(self, **kwargs)

    async def delete_api_key(self, api_key: str) -> dict[str, Any]:
        return await api_keys.delete_api_key(self, api_key)

    # --- Communications ---

    async def get_communications_id(self) -> dict[str, Any]:
        return await communications.get_communications_id(self)

    async def get_rfqs(self, **kwargs: Any) -> dict[str, Any]:
        return await communications.get_rfqs(self, **kwargs)

    async def create_rfq(self, **kwargs: Any) -> dict[str, Any]:
        return await communications.create_rfq(self, **kwargs)

    async def get_rfq(self, rfq_id: str) -> dict[str, Any]:
        return await communications.get_rfq(self, rfq_id)

    async def delete_rfq(self, rfq_id: str) -> dict[str, Any]:
        return await communications.delete_rfq(self, rfq_id)

    async def get_quotes(self, **kwargs: Any) -> dict[str, Any]:
        return await communications.get_quotes(self, **kwargs)

    async def create_quote(self, **kwargs: Any) -> dict[str, Any]:
        return await communications.create_quote(self, **kwargs)

    async def get_quote(self, quote_id: str) -> dict[str, Any]:
        return await communications.get_quote(self, quote_id)

    async def delete_quote(self, quote_id: str) -> dict[str, Any]:
        return await communications.delete_quote(self, quote_id)

    async def accept_quote(self, quote_id: str) -> dict[str, Any]:
        return await communications.accept_quote(self, quote_id)

    # --- Live Data ---

    async def get_live_data(self, milestone_id: str, **kwargs: Any) -> dict[str, Any]:
        return await live_data.get_live_data(self, milestone_id, **kwargs)

    async def get_live_data_legacy(self, data_type: str, milestone_id: str, **kwargs: Any) -> dict[str, Any]:
        return await live_data.get_live_data_legacy(self, data_type, milestone_id, **kwargs)

    async def get_live_data_batch(self, milestone_ids: List[str], **kwargs: Any) -> dict[str, Any]:
        return await live_data.get_live_data_batch(self, milestone_ids, **kwargs)

    async def get_game_stats(self, milestone_id: str) -> dict[str, Any]:
        return await live_data.get_game_stats(self, milestone_id)

    # --- Milestones ---

    async def get_milestone(self, milestone_id: str) -> dict[str, Any]:
        return await milestones.get_milestone(self, milestone_id)

    async def get_milestones(self, **kwargs: Any) -> dict[str, Any]:
        return await milestones.get_milestones(self, **kwargs)

    # --- Structured Targets ---

    async def get_structured_targets(self, **kwargs: Any) -> dict[str, Any]:
        return await structured_targets.get_structured_targets(self, **kwargs)

    async def get_structured_target(self, structured_target_id: str) -> dict[str, Any]:
        return await structured_targets.get_structured_target(self, structured_target_id)

    # --- Incentive Programs ---

    async def get_incentive_programs(self, **kwargs: Any) -> dict[str, Any]:
        return await incentive_programs.get_incentive_programs(self, **kwargs)
