"""Async HTTP client for the Kalshi API."""

from __future__ import annotations

import asyncio
import logging
import random
import re
import time
from typing import Any, Optional

import httpx

from .auth import KalshiCredentials
from .config import ClientConfig
from .exceptions import KalshiAPIError, KalshiRateLimitError
from .models.core import ExchangeStatus
from .models.responses import (
    AmendOrderResponse,
    AmendOrderV2Response,
    BatchCancelOrdersResponse,
    BatchCancelOrdersV2Response,
    BatchCreateOrdersResponse,
    BatchCreateOrdersV2Response,
    BatchGetMarketCandlesticksResponse,
    CancelOrderResponse,
    CancelOrderV2Response,
    CreateMarketInMultivariateEventCollectionResponse,
    CreateOrderV2Response,
    CreateApiKeyResponse,
    CreateOrderGroupResponse,
    CreateOrderResponse,
    CreateQuoteResponse,
    CreateRFQResponse,
    DecreaseOrderResponse,
    DecreaseOrderV2Response,
    EmptyResponse,
    GenerateApiKeyResponse,
    GetAccountApiLimitsResponse,
    GetAccountEndpointCostsResponse,
    GetApiKeysResponse,
    GetBalanceResponse,
    GetCommunicationsIDResponse,
    GetEventCandlesticksResponse,
    GetEventFeeChangesResponse,
    GetEventForecastPercentilesHistoryResponse,
    GetEventMetadataResponse,
    GetEventResponse,
    GetEventsResponse,
    GetExchangeAnnouncementsResponse,
    GetExchangeScheduleResponse,
    GetDepositsResponse,
    GetFillsResponse,
    GetFiltersBySportsResponse,
    GetGameStatsResponse,
    GetHistoricalCutoffResponse,
    GetIncentiveProgramsResponse,
    GetLiveDataResponse,
    GetLiveDatasResponse,
    GetMarketCandlesticksHistoricalResponse,
    GetMarketCandlesticksResponse,
    GetMarketOrderbookResponse,
    GetMarketOrderbooksResponse,
    GetMarketResponse,
    GetMarketsResponse,
    GetMilestoneResponse,
    GetMilestonesResponse,
    GetMultivariateEventCollectionLookupHistoryResponse,
    GetMultivariateEventCollectionResponse,
    GetMultivariateEventCollectionsResponse,
    GetMultivariateEventsResponse,
    GetOrderGroupResponse,
    GetOrderGroupsResponse,
    GetOrderQueuePositionResponse,
    GetOrderQueuePositionsResponse,
    GetOrderResponse,
    GetOrdersResponse,
    GetPositionsResponse,
    GetQuoteResponse,
    GetQuotesResponse,
    GetRFQResponse,
    GetRFQsResponse,
    GetSeriesFeeChangesResponse,
    GetSeriesListResponse,
    GetSeriesResponse,
    GetSettlementsResponse,
    GetStructuredTargetResponse,
    GetStructuredTargetsResponse,
    GetTagsForSeriesCategoriesResponse,
    GetTradesResponse,
    GetUserDataTimestampResponse,
    GetWithdrawalsResponse,
    LookupTickersForMarketInMultivariateEventCollectionResponse,
)
from .rate_limiter import ReadWriteTokenBucket
from ._observability import get_meter, get_tracer
from .api import (
    account,
    api_keys,
    communications,
    event_orders,
    events,
    exchange,
    historical,
    incentive_programs,
    live_data,
    markets,
    milestones,
    multivariate_collections,
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

        client_kwargs: dict[str, Any] = {
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

        # Rate limit auto-configuration state
        self._default_cost: float = 1.0  # conservative until configured
        self._cost_patterns: list[tuple[re.Pattern[str], str, float]] = []
        self._rates_configured = False
        self._rates_configuring = False
        self._rates_lock = asyncio.Lock()
        self._auto_configure = config.auto_configure_rates and rate_limiter is None

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

    # --- Rate limit auto-configuration ---

    async def configure_rate_limits(self) -> None:
        """Fetch rate limits and endpoint costs from the API and apply them.

        Called automatically on first request when ``auto_configure_rates`` is
        enabled (the default).  Can also be called explicitly for eager init.

        On failure the client falls back to the defaults from ``ClientConfig``
        and does not retry automatically.
        """
        async with self._rates_lock:
            if self._rates_configured:
                return
            self._rates_configuring = True
            try:
                await self._fetch_and_apply_rate_config()
            except Exception:
                logger.warning(
                    "Failed to fetch rate limits from API; using fallback defaults",
                    exc_info=True,
                )
            finally:
                self._rates_configuring = False
                self._rates_configured = True  # don't retry on failure

    async def _fetch_and_apply_rate_config(self) -> None:
        limits = await self.get_api_limits()
        await self._limiter.reconfigure(
            read_rate=float(limits.read.refill_rate),
            write_rate=float(limits.write.refill_rate),
            read_capacity=float(limits.read.bucket_capacity),
            write_capacity=float(limits.write.bucket_capacity),
        )
        logger.info(
            "Rate limits configured: read=%d/%d write=%d/%d (rate/capacity)",
            limits.read.refill_rate,
            limits.read.bucket_capacity,
            limits.write.refill_rate,
            limits.write.bucket_capacity,
        )

        costs = await self.get_endpoint_costs()
        self._default_cost = float(costs.default_cost)
        patterns: list[tuple[re.Pattern[str], str, float]] = []
        for ec in costs.endpoint_costs:
            # Kalshi returns paths with :param placeholders (e.g. :order_id).
            # Replace params first, then escape literals for safety.
            _marker = "\x00"
            marked = re.sub(r":[A-Za-z_][A-Za-z0-9_]*", _marker, ec.path)
            escaped = re.escape(marked)
            regex = escaped.replace(re.escape(_marker), "[^/]+")
            patterns.append((
                re.compile(f"^{regex}$"),
                ec.method.upper(),
                float(ec.cost),
            ))
        self._cost_patterns = patterns
        logger.info(
            "Endpoint costs configured: default=%d, %d non-default endpoints",
            costs.default_cost,
            len(costs.endpoint_costs),
        )

    async def _ensure_rates_configured(self) -> None:
        if self._rates_configured or self._rates_configuring or not self._auto_configure:
            return
        await self.configure_rate_limits()

    def _resolve_cost(self, method: str, path: str) -> float:
        upper_method = method.upper()
        for pattern, m, cost in self._cost_patterns:
            if m == upper_method and pattern.match(path):
                return cost
        return self._default_cost

    # --- Core request engine ---

    async def _execute_request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute request with rate limiting and 429 retry."""
        await self._ensure_rates_configured()

        cost = self._resolve_cost(method, path)
        if method.upper() == "GET":
            read_cost, write_cost = cost, 0.0
        else:
            read_cost, write_cost = 0.0, cost

        wait_start = time.monotonic()
        await self._limiter.acquire(read_cost=read_cost, write_cost=write_cost)
        waited = time.monotonic() - wait_start
        if waited > 0.001:
            self._rate_limiter_wait.record(waited)

        headers = {**kwargs.pop("headers", {}), **self._credentials.auth_headers(method, path)}
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
                    wait_time = self._config.base_retry_delay * (
                        2 ** retries
                    ) * random.uniform(0.5, 1.5)
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
                result = response.json()
                if not isinstance(result, dict):
                    raise KalshiAPIError(
                        status_code=response.status_code,
                        body=response.text,
                        method=method,
                        path=path,
                    )
                return result

            except httpx.RequestError as e:
                if retries >= self._config.max_retries:
                    logger.error("Network error after %d retries: %s", retries, e)
                    raise
                wait_time = self._config.base_retry_delay * (
                    2 ** retries
                ) * random.uniform(0.5, 1.5)
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
        self, path: str, params: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        return await self._execute_request("GET", path, params=params or {})

    async def post(
        self, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._execute_request("POST", path, json=body)

    async def put(
        self,
        path: str,
        body: dict[str, Any],
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return await self._execute_request(
            "PUT", path, json=body, **({"params": params} if params else {})
        )

    async def delete(
        self,
        path: str,
        body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if body is not None:
            kwargs["json"] = body
        return await self._execute_request("DELETE", path, **kwargs)

    # --- Exchange ---

    async def get_exchange_status(self) -> ExchangeStatus:
        data = await exchange.get_exchange_status(self)
        return ExchangeStatus.model_validate(data)

    async def get_exchange_schedule(self) -> GetExchangeScheduleResponse:
        data = await exchange.get_exchange_schedule(self)
        return GetExchangeScheduleResponse.model_validate(data)

    async def get_exchange_announcements(self) -> GetExchangeAnnouncementsResponse:
        data = await exchange.get_exchange_announcements(self)
        return GetExchangeAnnouncementsResponse.model_validate(data)

    async def get_user_data_timestamp(self) -> GetUserDataTimestampResponse:
        data = await exchange.get_user_data_timestamp(self)
        return GetUserDataTimestampResponse.model_validate(data)

    # --- Account ---

    async def get_api_limits(self) -> GetAccountApiLimitsResponse:
        data = await account.get_api_limits(self)
        return GetAccountApiLimitsResponse.model_validate(data)

    async def get_endpoint_costs(self) -> GetAccountEndpointCostsResponse:
        data = await account.get_endpoint_costs(self)
        return GetAccountEndpointCostsResponse.model_validate(data)

    # --- Orders ---

    async def get_orders(self, **kwargs: Any) -> GetOrdersResponse:
        data = await orders.get_orders(self, **kwargs)
        return GetOrdersResponse.model_validate(data)

    async def get_order(self, order_id: str) -> GetOrderResponse:
        data = await orders.get_order(self, order_id)
        return GetOrderResponse.model_validate(data)

    async def create_order(self, **kwargs: Any) -> CreateOrderResponse:
        data = await orders.create_order(self, **kwargs)
        self._orders_created.add(1)
        return CreateOrderResponse.model_validate(data)

    async def cancel_order(self, order_id: str) -> CancelOrderResponse:
        data = await orders.cancel_order(self, order_id)
        self._orders_cancelled.add(1)
        return CancelOrderResponse.model_validate(data)

    async def amend_order(self, order_id: str, **kwargs: Any) -> AmendOrderResponse:
        data = await orders.amend_order(self, order_id, **kwargs)
        return AmendOrderResponse.model_validate(data)

    async def decrease_order(self, order_id: str, **kwargs: Any) -> DecreaseOrderResponse:
        data = await orders.decrease_order(self, order_id, **kwargs)
        return DecreaseOrderResponse.model_validate(data)

    async def batch_create_orders(
        self, orders_list: list[dict[str, Any]]
    ) -> BatchCreateOrdersResponse:
        data = await orders.batch_create_orders(self, orders_list)
        return BatchCreateOrdersResponse.model_validate(data)

    async def batch_cancel_orders(self, order_ids: list[str]) -> BatchCancelOrdersResponse:
        data = await orders.batch_cancel_orders(self, order_ids)
        return BatchCancelOrdersResponse.model_validate(data)

    async def get_queue_positions(self, **kwargs: Any) -> GetOrderQueuePositionsResponse:
        data = await orders.get_queue_positions(self, **kwargs)
        return GetOrderQueuePositionsResponse.model_validate(data)

    async def get_order_queue_position(self, order_id: str) -> GetOrderQueuePositionResponse:
        data = await orders.get_order_queue_position(self, order_id)
        return GetOrderQueuePositionResponse.model_validate(data)

    # --- Order Groups ---

    async def get_order_groups(self) -> GetOrderGroupsResponse:
        data = await order_groups.get_order_groups(self)
        return GetOrderGroupsResponse.model_validate(data)

    async def create_order_group(self, contracts_limit: int) -> CreateOrderGroupResponse:
        data = await order_groups.create_order_group(self, contracts_limit)
        return CreateOrderGroupResponse.model_validate(data)

    async def get_order_group(self, order_group_id: str) -> GetOrderGroupResponse:
        data = await order_groups.get_order_group(self, order_group_id)
        return GetOrderGroupResponse.model_validate(data)

    async def delete_order_group(self, order_group_id: str) -> EmptyResponse:
        data = await order_groups.delete_order_group(self, order_group_id)
        return EmptyResponse.model_validate(data)

    async def reset_order_group(self, order_group_id: str) -> EmptyResponse:
        data = await order_groups.reset_order_group(self, order_group_id)
        return EmptyResponse.model_validate(data)

    async def trigger_order_group(self, order_group_id: str, **kwargs: Any) -> EmptyResponse:
        data = await order_groups.trigger_order_group(self, order_group_id, **kwargs)
        return EmptyResponse.model_validate(data)

    async def update_order_group_limit(self, order_group_id: str, **kwargs: Any) -> EmptyResponse:
        data = await order_groups.update_order_group_limit(self, order_group_id, **kwargs)
        return EmptyResponse.model_validate(data)

    # --- Portfolio ---

    async def get_balance(self) -> GetBalanceResponse:
        data = await portfolio.get_balance(self)
        return GetBalanceResponse.model_validate(data)

    async def get_positions(self, **kwargs: Any) -> GetPositionsResponse:
        data = await portfolio.get_positions(self, **kwargs)
        return GetPositionsResponse.model_validate(data)

    async def get_settlements(self) -> GetSettlementsResponse:
        data = await portfolio.get_settlements(self)
        return GetSettlementsResponse.model_validate(data)

    async def get_fills(self) -> GetFillsResponse:
        data = await portfolio.get_fills(self)
        return GetFillsResponse.model_validate(data)

    async def get_deposits(self, **kwargs: Any) -> GetDepositsResponse:
        data = await portfolio.get_deposits(self, **kwargs)
        return GetDepositsResponse.model_validate(data)

    async def get_withdrawals(self, **kwargs: Any) -> GetWithdrawalsResponse:
        data = await portfolio.get_withdrawals(self, **kwargs)
        return GetWithdrawalsResponse.model_validate(data)

    # --- Markets ---

    async def get_market(self, ticker: str) -> GetMarketResponse:
        data = await markets.get_market(self, ticker)
        return GetMarketResponse.model_validate(data)

    async def get_markets(self, **kwargs: Any) -> GetMarketsResponse:
        data = await markets.get_markets(self, **kwargs)
        return GetMarketsResponse.model_validate(data)

    async def get_market_orderbook(self, ticker: str, **kwargs: Any) -> GetMarketOrderbookResponse:
        data = await markets.get_market_orderbook(self, ticker, **kwargs)
        return GetMarketOrderbookResponse.model_validate(data)

    async def get_market_orderbooks(self, tickers: list[str]) -> GetMarketOrderbooksResponse:
        data = await markets.get_market_orderbooks(self, tickers)
        return GetMarketOrderbooksResponse.model_validate(data)

    async def get_batch_market_candlesticks(
        self, market_tickers: list[str], **kwargs: Any
    ) -> BatchGetMarketCandlesticksResponse:
        data = await markets.get_batch_market_candlesticks(self, market_tickers, **kwargs)
        return BatchGetMarketCandlesticksResponse.model_validate(data)

    async def get_market_candlesticks(
        self, series_ticker: str, ticker: str, **kwargs: Any
    ) -> GetMarketCandlesticksResponse:
        data = await markets.get_market_candlesticks(self, series_ticker, ticker, **kwargs)
        return GetMarketCandlesticksResponse.model_validate(data)

    async def get_trades(self, **kwargs: Any) -> GetTradesResponse:
        data = await markets.get_trades(self, **kwargs)
        return GetTradesResponse.model_validate(data)

    # --- Events ---

    async def get_event(self, event_ticker: str, **kwargs: Any) -> GetEventResponse:
        data = await events.get_event(self, event_ticker, **kwargs)
        return GetEventResponse.model_validate(data)

    async def get_events(self, **kwargs: Any) -> GetEventsResponse:
        data = await events.get_events(self, **kwargs)
        return GetEventsResponse.model_validate(data)

    async def get_multivariate_events(self, **kwargs: Any) -> GetMultivariateEventsResponse:
        data = await events.get_multivariate_events(self, **kwargs)
        return GetMultivariateEventsResponse.model_validate(data)

    async def get_event_metadata(self, event_ticker: str) -> GetEventMetadataResponse:
        data = await events.get_event_metadata(self, event_ticker)
        return GetEventMetadataResponse.model_validate(data)

    async def get_event_fee_changes(self, **kwargs: Any) -> GetEventFeeChangesResponse:
        data = await events.get_event_fee_changes(self, **kwargs)
        return GetEventFeeChangesResponse.model_validate(data)

    async def get_event_candlesticks(
        self, series_ticker: str, event_ticker: str, **kwargs: Any
    ) -> GetEventCandlesticksResponse:
        data = await events.get_event_candlesticks(self, series_ticker, event_ticker, **kwargs)
        return GetEventCandlesticksResponse.model_validate(data)

    async def get_forecast_percentile_history(
        self, series_ticker: str, event_ticker: str, **kwargs: Any
    ) -> GetEventForecastPercentilesHistoryResponse:
        data = await events.get_forecast_percentile_history(
            self, series_ticker, event_ticker, **kwargs
        )
        return GetEventForecastPercentilesHistoryResponse.model_validate(data)

    # --- Series ---

    async def get_series(self, series_ticker: str, **kwargs: Any) -> GetSeriesResponse:
        data = await series.get_series(self, series_ticker, **kwargs)
        return GetSeriesResponse.model_validate(data)

    async def get_series_list(self, **kwargs: Any) -> GetSeriesListResponse:
        data = await series.get_series_list(self, **kwargs)
        return GetSeriesListResponse.model_validate(data)

    async def get_fee_changes(self, **kwargs: Any) -> GetSeriesFeeChangesResponse:
        data = await series.get_fee_changes(self, **kwargs)
        return GetSeriesFeeChangesResponse.model_validate(data)

    # --- Search ---

    async def get_tags_by_categories(self) -> GetTagsForSeriesCategoriesResponse:
        data = await search.get_tags_by_categories(self)
        # Kalshi returns null for some categories' tag lists (e.g. Social);
        # coalesce to [] so the model stays dict[str, list[str]].
        raw = data.get("tags_by_categories")
        if isinstance(raw, dict):
            data = {**data, "tags_by_categories": {k: v or [] for k, v in raw.items()}}
        return GetTagsForSeriesCategoriesResponse.model_validate(data)

    async def get_filters_by_sport(self) -> GetFiltersBySportsResponse:
        data = await search.get_filters_by_sport(self)
        return GetFiltersBySportsResponse.model_validate(data)

    # --- Historical ---

    async def get_historical_cutoff(self) -> GetHistoricalCutoffResponse:
        data = await historical.get_cutoff(self)
        return GetHistoricalCutoffResponse.model_validate(data)

    async def get_historical_markets(self, **kwargs: Any) -> GetMarketsResponse:
        data = await historical.get_historical_markets(self, **kwargs)
        return GetMarketsResponse.model_validate(data)

    async def get_historical_market(self, ticker: str) -> GetMarketResponse:
        data = await historical.get_historical_market(self, ticker)
        return GetMarketResponse.model_validate(data)

    async def get_historical_market_candlesticks(
        self, ticker: str, **kwargs: Any
    ) -> GetMarketCandlesticksHistoricalResponse:
        data = await historical.get_historical_market_candlesticks(self, ticker, **kwargs)
        return GetMarketCandlesticksHistoricalResponse.model_validate(data)

    async def get_historical_fills(self, **kwargs: Any) -> GetFillsResponse:
        data = await historical.get_historical_fills(self, **kwargs)
        return GetFillsResponse.model_validate(data)

    async def get_historical_orders(self, **kwargs: Any) -> GetOrdersResponse:
        data = await historical.get_historical_orders(self, **kwargs)
        return GetOrdersResponse.model_validate(data)

    async def get_historical_trades(self, **kwargs: Any) -> GetTradesResponse:
        data = await historical.get_historical_trades(self, **kwargs)
        return GetTradesResponse.model_validate(data)

    # --- API Keys ---

    async def get_api_keys(self) -> GetApiKeysResponse:
        data = await api_keys.get_api_keys(self)
        return GetApiKeysResponse.model_validate(data)

    async def create_api_key(self, **kwargs: Any) -> CreateApiKeyResponse:
        data = await api_keys.create_api_key(self, **kwargs)
        return CreateApiKeyResponse.model_validate(data)

    async def generate_api_key(self, **kwargs: Any) -> GenerateApiKeyResponse:
        data = await api_keys.generate_api_key(self, **kwargs)
        return GenerateApiKeyResponse.model_validate(data)

    async def delete_api_key(self, api_key: str) -> EmptyResponse:
        data = await api_keys.delete_api_key(self, api_key)
        return EmptyResponse.model_validate(data)

    # --- Communications ---

    async def get_communications_id(self) -> GetCommunicationsIDResponse:
        data = await communications.get_communications_id(self)
        return GetCommunicationsIDResponse.model_validate(data)

    async def get_rfqs(self, **kwargs: Any) -> GetRFQsResponse:
        data = await communications.get_rfqs(self, **kwargs)
        return GetRFQsResponse.model_validate(data)

    async def create_rfq(self, **kwargs: Any) -> CreateRFQResponse:
        data = await communications.create_rfq(self, **kwargs)
        return CreateRFQResponse.model_validate(data)

    async def get_rfq(self, rfq_id: str) -> GetRFQResponse:
        data = await communications.get_rfq(self, rfq_id)
        return GetRFQResponse.model_validate(data)

    async def delete_rfq(self, rfq_id: str) -> EmptyResponse:
        data = await communications.delete_rfq(self, rfq_id)
        return EmptyResponse.model_validate(data)

    async def get_quotes(self, **kwargs: Any) -> GetQuotesResponse:
        data = await communications.get_quotes(self, **kwargs)
        return GetQuotesResponse.model_validate(data)

    async def create_quote(self, **kwargs: Any) -> CreateQuoteResponse:
        data = await communications.create_quote(self, **kwargs)
        return CreateQuoteResponse.model_validate(data)

    async def get_quote(self, quote_id: str) -> GetQuoteResponse:
        data = await communications.get_quote(self, quote_id)
        return GetQuoteResponse.model_validate(data)

    async def delete_quote(self, quote_id: str) -> EmptyResponse:
        data = await communications.delete_quote(self, quote_id)
        return EmptyResponse.model_validate(data)

    async def confirm_quote(self, quote_id: str) -> EmptyResponse:
        data = await communications.confirm_quote(self, quote_id)
        return EmptyResponse.model_validate(data)

    async def accept_quote(self, quote_id: str) -> EmptyResponse:
        data = await communications.accept_quote(self, quote_id)
        return EmptyResponse.model_validate(data)

    # --- Live Data ---

    async def get_live_data(self, milestone_id: str, **kwargs: Any) -> GetLiveDataResponse:
        data = await live_data.get_live_data(self, milestone_id, **kwargs)
        return GetLiveDataResponse.model_validate(data)

    async def get_live_data_legacy(
        self, data_type: str, milestone_id: str, **kwargs: Any
    ) -> GetLiveDataResponse:
        data = await live_data.get_live_data_legacy(self, data_type, milestone_id, **kwargs)
        return GetLiveDataResponse.model_validate(data)

    async def get_live_data_batch(
        self, milestone_ids: list[str], **kwargs: Any
    ) -> GetLiveDatasResponse:
        data = await live_data.get_live_data_batch(self, milestone_ids, **kwargs)
        return GetLiveDatasResponse.model_validate(data)

    async def get_game_stats(self, milestone_id: str) -> GetGameStatsResponse:
        data = await live_data.get_game_stats(self, milestone_id)
        return GetGameStatsResponse.model_validate(data)

    # --- Milestones ---

    async def get_milestone(self, milestone_id: str) -> GetMilestoneResponse:
        data = await milestones.get_milestone(self, milestone_id)
        return GetMilestoneResponse.model_validate(data)

    async def get_milestones(self, **kwargs: Any) -> GetMilestonesResponse:
        data = await milestones.get_milestones(self, **kwargs)
        return GetMilestonesResponse.model_validate(data)

    # --- Structured Targets ---

    async def get_structured_targets(self, **kwargs: Any) -> GetStructuredTargetsResponse:
        data = await structured_targets.get_structured_targets(self, **kwargs)
        return GetStructuredTargetsResponse.model_validate(data)

    async def get_structured_target(self, structured_target_id: str) -> GetStructuredTargetResponse:
        data = await structured_targets.get_structured_target(self, structured_target_id)
        return GetStructuredTargetResponse.model_validate(data)

    # --- Incentive Programs ---

    async def get_incentive_programs(self, **kwargs: Any) -> GetIncentiveProgramsResponse:
        data = await incentive_programs.get_incentive_programs(self, **kwargs)
        return GetIncentiveProgramsResponse.model_validate(data)

    # --- Event Orders (V2) ---

    async def create_event_order(self, **kwargs: Any) -> CreateOrderV2Response:
        data = await event_orders.create_event_order(self, **kwargs)
        return CreateOrderV2Response.model_validate(data)

    async def cancel_event_order(self, order_id: str) -> CancelOrderV2Response:
        data = await event_orders.cancel_event_order(self, order_id)
        return CancelOrderV2Response.model_validate(data)

    async def amend_event_order(self, order_id: str, **kwargs: Any) -> AmendOrderV2Response:
        data = await event_orders.amend_event_order(self, order_id, **kwargs)
        return AmendOrderV2Response.model_validate(data)

    async def decrease_event_order(self, order_id: str, **kwargs: Any) -> DecreaseOrderV2Response:
        data = await event_orders.decrease_event_order(self, order_id, **kwargs)
        return DecreaseOrderV2Response.model_validate(data)

    async def batch_create_event_orders(
        self, orders_list: list[dict[str, Any]]
    ) -> BatchCreateOrdersV2Response:
        data = await event_orders.batch_create_event_orders(self, orders_list)
        return BatchCreateOrdersV2Response.model_validate(data)

    async def batch_cancel_event_orders(
        self, orders_list: list[dict[str, Any]]
    ) -> BatchCancelOrdersV2Response:
        data = await event_orders.batch_cancel_event_orders(self, orders_list)
        return BatchCancelOrdersV2Response.model_validate(data)

    # --- Multivariate Event Collections ---

    async def get_multivariate_event_collections(
        self, **kwargs: Any
    ) -> GetMultivariateEventCollectionsResponse:
        data = await multivariate_collections.get_multivariate_event_collections(self, **kwargs)
        return GetMultivariateEventCollectionsResponse.model_validate(data)

    async def get_multivariate_event_collection(
        self, collection_ticker: str
    ) -> GetMultivariateEventCollectionResponse:
        data = await multivariate_collections.get_multivariate_event_collection(
            self, collection_ticker
        )
        return GetMultivariateEventCollectionResponse.model_validate(data)

    async def get_multivariate_event_collection_lookup_history(
        self, collection_ticker: str, **kwargs: Any
    ) -> GetMultivariateEventCollectionLookupHistoryResponse:
        data = await multivariate_collections.get_multivariate_event_collection_lookup_history(
            self, collection_ticker, **kwargs
        )
        return GetMultivariateEventCollectionLookupHistoryResponse.model_validate(data)

    async def create_market_in_multivariate_event_collection(
        self, collection_ticker: str, **kwargs: Any
    ) -> CreateMarketInMultivariateEventCollectionResponse:
        data = await multivariate_collections.create_market_in_multivariate_event_collection(
            self, collection_ticker, **kwargs
        )
        return CreateMarketInMultivariateEventCollectionResponse.model_validate(data)

    async def lookup_tickers_in_multivariate_event_collection(
        self, collection_ticker: str, **kwargs: Any
    ) -> LookupTickersForMarketInMultivariateEventCollectionResponse:
        data = await multivariate_collections.lookup_tickers_in_multivariate_event_collection(
            self, collection_ticker, **kwargs
        )
        return LookupTickersForMarketInMultivariateEventCollectionResponse.model_validate(data)
