"""Tests for pykalshi.http_client — typed API methods + core engine."""

import pytest

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient
from pykalshi.exceptions import KalshiAPIError, KalshiRateLimitError
from pykalshi.testing.mock_transport import make_mock_transport
from pykalshi.testing.fixtures import mock_credentials, test_config as _test_config

from .mock_data import (
    MOCK_EVENT, MOCK_LIVE_DATA, MOCK_MARKET, MOCK_MILESTONE,
    MOCK_ORDER, MOCK_SERIES, MOCK_TRADE,
)


@pytest.fixture
def creds() -> KalshiCredentials:
    return mock_credentials()


@pytest.fixture
def cfg() -> ClientConfig:
    return _test_config()


def _client(creds: KalshiCredentials, cfg: ClientConfig, routes: dict) -> KalshiHttpClient:
    return KalshiHttpClient(creds, cfg, transport=make_mock_transport(routes))


# =============================================================================
# Core Engine
# =============================================================================


class TestCoreEngine:
    @pytest.mark.asyncio
    async def test_api_error_raised(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {("GET", "/trade-api/v2/exchange/status"): 500}) as c:
            with pytest.raises(KalshiAPIError) as exc_info:
                await c.get_exchange_status()
            assert exc_info.value.status_code == 500
            assert exc_info.value.method == "GET"

    @pytest.mark.asyncio
    async def test_429_retries_then_raises(self, creds: KalshiCredentials) -> None:
        cfg = ClientConfig(
            environment=Environment.DEMO,
            http_base_url="http://localhost:0",
            max_retries=1,
            base_retry_delay=0.01,
        )
        async with _client(creds, cfg, {("GET", "/trade-api/v2/exchange/status"): 429}) as c:
            with pytest.raises(KalshiRateLimitError):
                await c.get_exchange_status()

    @pytest.mark.asyncio
    async def test_context_manager(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        client = _client(creds, cfg, {})
        async with client:
            pass


# =============================================================================
# Exchange
# =============================================================================


class TestExchange:
    @pytest.mark.asyncio
    async def test_get_exchange_status(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/status"): {
            "exchange_active": True, "trading_active": True
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_status()
            assert result.exchange_active is True
            assert result.trading_active is True

    @pytest.mark.asyncio
    async def test_get_exchange_schedule(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/schedule"): {
            "schedule": {"standard_hours": [], "maintenance_windows": []}
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_schedule()
            assert result.schedule is not None

    @pytest.mark.asyncio
    async def test_get_exchange_announcements(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/announcements"): {"announcements": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_announcements()
            assert result.announcements == []

    @pytest.mark.asyncio
    async def test_get_user_data_timestamp(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/user_data_timestamp"): {
            "as_of_time": "2024-01-01T00:00:00Z"
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_user_data_timestamp()
            assert result.as_of_time == "2024-01-01T00:00:00Z"


# =============================================================================
# Account
# =============================================================================


class TestAccount:
    @pytest.mark.asyncio
    async def test_get_api_limits(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/account/limits"): {
            "usage_tier": "standard", "read_limit": 20, "write_limit": 10
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_api_limits()
            assert result.read_limit == 20
            assert result.write_limit == 10

    @pytest.mark.asyncio
    async def test_get_endpoint_costs(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/account/endpoint_costs"): {
            "default_cost": 10, "endpoint_costs": []
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_endpoint_costs()
            assert result.default_cost == 10


# =============================================================================
# Orders
# =============================================================================


class TestOrders:
    @pytest.mark.asyncio
    async def test_get_orders(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {
            "orders": [MOCK_ORDER], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_orders(status="resting", limit=10)
            assert len(result.orders) == 1
            assert result.orders[0].order_id == "ord-123"

    @pytest.mark.asyncio
    async def test_get_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"order": MOCK_ORDER}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order("ord-123")
            assert result.order.order_id == "ord-123"

    @pytest.mark.asyncio
    async def test_create_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"order": MOCK_ORDER}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_order(
                ticker="KXBTC-100K", side="yes", action="buy",
                count=10, yes_price=50,
            )
            assert result.order.order_id == "ord-123"

    @pytest.mark.asyncio
    async def test_cancel_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/portfolio/orders"): {
            "order": {**MOCK_ORDER, "status": "canceled"}, "reduced_by_fp": "10"
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.cancel_order("ord-123")
            assert result.order.status.value == "canceled"
            assert result.reduced_by_fp == "10"

    @pytest.mark.asyncio
    async def test_amend_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {
            "old_order": MOCK_ORDER,
            "order": {**MOCK_ORDER, "yes_price_dollars": "0.55"},
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.amend_order(
                "ord-123",
                ticker="KXBTC-100K", side="yes", action="buy",
                client_order_id="old", updated_client_order_id="new",
                yes_price=55,
            )
            assert result.order.yes_price_dollars == "0.55"

    @pytest.mark.asyncio
    async def test_decrease_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {
            "order": {**MOCK_ORDER, "remaining_count_fp": "5"}
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.decrease_order("ord-123", reduce_to=5)
            assert result.order.remaining_count_fp == "5"

    @pytest.mark.asyncio
    async def test_get_queue_positions(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"queue_positions": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_queue_positions(event_ticker="EVT-1")
            assert result.queue_positions == []

    @pytest.mark.asyncio
    async def test_get_order_queue_position(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"queue_position_fp": "3"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order_queue_position("ord-123")
            assert result.queue_position_fp == "3"


# =============================================================================
# Order Groups
# =============================================================================


class TestOrderGroups:
    @pytest.mark.asyncio
    async def test_get_order_groups(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/order_groups"): {"order_groups": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order_groups()
            assert result.order_groups == []

    @pytest.mark.asyncio
    async def test_create_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/order_groups"): {
            "order_group_id": "grp-1"
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_order_group(contracts_limit=100)
            assert result.order_group_id == "grp-1"

    @pytest.mark.asyncio
    async def test_get_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/order_groups"): {
            "is_auto_cancel_enabled": True, "orders": ["ord-1"]
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order_group("grp-1")
            assert result.is_auto_cancel_enabled is True

    @pytest.mark.asyncio
    async def test_delete_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/portfolio/order_groups"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_order_group("grp-1")
            assert result is not None

    @pytest.mark.asyncio
    async def test_reset_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("PUT", "/trade-api/v2/portfolio/order_groups"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.reset_order_group("grp-1")
            assert result is not None


# =============================================================================
# Portfolio
# =============================================================================


class TestPortfolio:
    @pytest.mark.asyncio
    async def test_get_balance(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/balance"): {
            "balance": 10000, "portfolio_value": 5000, "updated_ts": 1700000000
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_balance()
            assert result.balance == 10000
            assert result.portfolio_value == 5000

    @pytest.mark.asyncio
    async def test_get_positions(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/positions"): {
            "market_positions": [], "event_positions": []
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_positions(event_ticker="EVT-1")
            assert result.market_positions == []

    @pytest.mark.asyncio
    async def test_get_settlements(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/settlements"): {
            "settlements": []
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_settlements()
            assert result.settlements == []

    @pytest.mark.asyncio
    async def test_get_fills(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/fills"): {
            "fills": [], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_fills()
            assert result.fills == []


# =============================================================================
# Markets
# =============================================================================


class TestMarkets:
    @pytest.mark.asyncio
    async def test_get_market(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets"): {"market": MOCK_MARKET}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_market("KXBTC-100K")
            assert result.market.ticker == "KXBTC-100K"

    @pytest.mark.asyncio
    async def test_get_markets(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets"): {"markets": [], "cursor": ""}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_markets(status="open", limit=50)
            assert result.markets == []

    @pytest.mark.asyncio
    async def test_get_market_orderbook(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets"): {
            "orderbook_fp": {"yes_dollars": [], "no_dollars": []}
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_market_orderbook("KXBTC")
            assert result.orderbook_fp is not None

    @pytest.mark.asyncio
    async def test_get_trades(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets/trades"): {
            "trades": [MOCK_TRADE], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_trades(ticker="KXBTC", limit=10)
            assert len(result.trades) == 1


# =============================================================================
# Events
# =============================================================================


class TestEvents:
    @pytest.mark.asyncio
    async def test_get_event(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events"): {
            "event": MOCK_EVENT, "markets": []
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_event("EVT-1", with_nested_markets=True)
            assert result.event.event_ticker == "EVT-1"

    @pytest.mark.asyncio
    async def test_get_events(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events"): {"events": [], "cursor": ""}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_events(status="open", limit=10)
            assert result.events == []

    @pytest.mark.asyncio
    async def test_get_multivariate_events(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events/multivariate"): {
            "events": [], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_multivariate_events(limit=5)
            assert result.events == []

    @pytest.mark.asyncio
    async def test_get_event_metadata(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events/EVT-1"): {
            "image_url": "https://example.com/img.png",
            "market_details": [],
            "settlement_sources": [],
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_event_metadata("EVT-1")
            assert result.image_url == "https://example.com/img.png"


# =============================================================================
# Series
# =============================================================================


class TestSeries:
    @pytest.mark.asyncio
    async def test_get_series(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series"): {"series": MOCK_SERIES}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_series("KXBTC", include_volume=True)
            assert result.series.ticker == "KXBTC"

    @pytest.mark.asyncio
    async def test_get_series_list(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series"): {"series": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_series_list(category="Crypto", limit=10)
            assert result.series == []


# =============================================================================
# Search
# =============================================================================


class TestSearch:
    @pytest.mark.asyncio
    async def test_get_tags_by_categories(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/search/tags_by_categories"): {
            "tags_by_categories": {"Crypto": ["BTC", "ETH"]}
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_tags_by_categories()
            assert "Crypto" in result.tags_by_categories

    @pytest.mark.asyncio
    async def test_get_filters_by_sport(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/search/filters_by_sport"): {
            "filters_by_sports": {}, "sport_ordering": ["NFL"]
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_filters_by_sport()
            assert result.sport_ordering == ["NFL"]


# =============================================================================
# Batch Operations
# =============================================================================


class TestBatchOperations:
    @pytest.mark.asyncio
    async def test_batch_create_orders(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"orders": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.batch_create_orders([])
            assert result.orders == []

    @pytest.mark.asyncio
    async def test_batch_cancel_orders(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/portfolio/orders"): {"orders": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.batch_cancel_orders([])
            assert result.orders == []

    @pytest.mark.asyncio
    async def test_batch_create_propagates_error(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): 500}
        async with _client(creds, cfg, routes) as c:
            with pytest.raises(KalshiAPIError):
                await c.batch_create_orders([
                    {"ticker": "T1", "side": "yes", "action": "buy", "count": 1},
                ])


# =============================================================================
# Historical
# =============================================================================


class TestHistorical:
    @pytest.mark.asyncio
    async def test_get_historical_cutoff(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/cutoff"): {
            "market_settled_ts": "2024-01-01T00:00:00Z",
            "trades_created_ts": "2024-01-01T00:00:00Z",
            "orders_updated_ts": "2024-01-01T00:00:00Z",
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_cutoff()
            assert result.market_settled_ts == "2024-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_get_historical_markets(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/markets"): {
            "markets": [], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_markets(limit=5)
            assert result.markets == []

    @pytest.mark.asyncio
    async def test_get_historical_fills(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/fills"): {
            "fills": [], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_fills(limit=10)
            assert result.fills == []

    @pytest.mark.asyncio
    async def test_get_historical_orders(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/orders"): {
            "orders": [], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_orders(limit=10)
            assert result.orders == []

    @pytest.mark.asyncio
    async def test_get_historical_trades(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/trades"): {
            "trades": [], "cursor": ""
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_trades(limit=10)
            assert result.trades == []


# =============================================================================
# API Keys
# =============================================================================


class TestApiKeys:
    @pytest.mark.asyncio
    async def test_get_api_keys(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/api_keys"): {"api_keys": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_api_keys()
            assert result.api_keys == []

    @pytest.mark.asyncio
    async def test_create_api_key(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/api_keys"): {"api_key_id": "new-key"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_api_key(public_key="ssh-rsa AAAA...", name="test")
            assert result.api_key_id == "new-key"

    @pytest.mark.asyncio
    async def test_generate_api_key(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/api_keys"): {
            "api_key_id": "gen-key", "private_key": "-----BEGIN RSA PRIVATE KEY-----\n..."
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.generate_api_key(name="test-key")
            assert result.api_key_id == "gen-key"

    @pytest.mark.asyncio
    async def test_delete_api_key(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/api_keys"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_api_key("key-to-delete")
            assert result is not None


# =============================================================================
# Communications
# =============================================================================


class TestCommunications:
    @pytest.mark.asyncio
    async def test_get_communications_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/id"): {
            "communications_id": "comm-123"
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_communications_id()
            assert result.communications_id == "comm-123"

    @pytest.mark.asyncio
    async def test_get_rfqs(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/rfqs"): {"rfqs": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_rfqs(limit=5)
            assert result.rfqs == []

    @pytest.mark.asyncio
    async def test_create_rfq(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/communications/rfqs"): {"id": "rfq-1"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_rfq(market_ticker="KXBTC", side="yes", size=100)
            assert result.id == "rfq-1"

    @pytest.mark.asyncio
    async def test_delete_rfq(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/communications/rfqs"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_rfq("rfq-1")
            assert result is not None

    @pytest.mark.asyncio
    async def test_get_quotes(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/quotes"): {"quotes": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_quotes(limit=5)
            assert result.quotes == []

    @pytest.mark.asyncio
    async def test_create_quote(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/communications/quotes"): {"id": "q-1"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_quote(rfq_id="rfq-1", price="0.50", size=50)
            assert result.id == "q-1"


# =============================================================================
# Live Data
# =============================================================================


class TestLiveData:
    @pytest.mark.asyncio
    async def test_get_live_data(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/live_data"): {"live_data": MOCK_LIVE_DATA}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_live_data("ms-1")
            assert result.live_data is not None

    @pytest.mark.asyncio
    async def test_get_live_data_batch(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/live_data/batch"): {"live_datas": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_live_data_batch(["ms-1", "ms-2"])
            assert result.live_datas == []

    @pytest.mark.asyncio
    async def test_get_game_stats(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/live_data/milestone"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_game_stats("ms-1")
            assert result.pbp is None


# =============================================================================
# Milestones
# =============================================================================


class TestMilestones:
    @pytest.mark.asyncio
    async def test_get_milestone(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/milestones"): {
            "milestone": MOCK_MILESTONE
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_milestone("ms-1")
            assert result.milestone.id == "ms-1"

    @pytest.mark.asyncio
    async def test_get_milestones(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/milestones"): {"milestones": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_milestones(limit=10)
            assert result.milestones == []


# =============================================================================
# Structured Targets
# =============================================================================


class TestStructuredTargets:
    @pytest.mark.asyncio
    async def test_get_structured_targets(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/structured_targets"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_structured_targets(competition="NFL")
            assert result.structured_targets is None

    @pytest.mark.asyncio
    async def test_get_structured_target(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/structured_targets"): {}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_structured_target("st-1")
            assert result.structured_target is None


# =============================================================================
# Incentive Programs
# =============================================================================


class TestIncentivePrograms:
    @pytest.mark.asyncio
    async def test_get_incentive_programs(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/incentive_programs"): {
            "incentive_programs": []
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_incentive_programs(status="active")
            assert result.incentive_programs == []


# =============================================================================
# Model Dump (raw dict access still works)
# =============================================================================


class TestModelDump:
    @pytest.mark.asyncio
    async def test_model_dump_returns_dict(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/status"): {
            "exchange_active": True, "trading_active": False
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_status()
            d = result.model_dump()
            assert isinstance(d, dict)
            assert d["exchange_active"] is True


# =============================================================================
# Gap 3: Empty path parameter validation
# =============================================================================


class TestEmptyPathParamValidation:
    @pytest.mark.asyncio
    async def test_get_order_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_id"):
                await c.get_order("")

    @pytest.mark.asyncio
    async def test_cancel_order_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_id"):
                await c.cancel_order("")

    @pytest.mark.asyncio
    async def test_amend_order_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_id"):
                await c.amend_order(
                    "", ticker="T", side="yes", action="buy",
                    client_order_id="a", updated_client_order_id="b",
                )

    @pytest.mark.asyncio
    async def test_decrease_order_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_id"):
                await c.decrease_order("", reduce_to=0)

    @pytest.mark.asyncio
    async def test_get_order_queue_position_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_id"):
                await c.get_order_queue_position("")

    @pytest.mark.asyncio
    async def test_delete_order_group_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_group_id"):
                await c.delete_order_group("")

    @pytest.mark.asyncio
    async def test_get_order_group_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_group_id"):
                await c.get_order_group("")

    @pytest.mark.asyncio
    async def test_reset_order_group_empty_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            with pytest.raises(ValueError, match="order_group_id"):
                await c.reset_order_group("")
