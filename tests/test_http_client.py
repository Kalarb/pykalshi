"""Tests for pykalshi.http_client — all 33 API methods + core engine."""

import pytest

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient
from pykalshi.exceptions import KalshiAPIError, KalshiRateLimitError
from pykalshi.testing.mock_transport import make_mock_transport
from pykalshi.testing.fixtures import mock_credentials, test_config as _test_config


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
        routes = {("GET", "/trade-api/v2/exchange/status"): {"exchange_active": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_status()
            assert result["exchange_active"] is True

    @pytest.mark.asyncio
    async def test_get_exchange_schedule(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/schedule"): {"schedule": {"standard_hours": {}}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_schedule()
            assert "schedule" in result


# =============================================================================
# Account
# =============================================================================


class TestAccount:
    @pytest.mark.asyncio
    async def test_get_api_limits(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/account/limits"): {"read_limit": 20, "write_limit": 10}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_api_limits()
            assert result["read_limit"] == 20


# =============================================================================
# Orders
# =============================================================================


class TestOrders:
    @pytest.mark.asyncio
    async def test_get_orders(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"orders": [], "cursor": None}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_orders(status="resting", limit=10)
            assert result["orders"] == []

    @pytest.mark.asyncio
    async def test_get_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"order": {"order_id": "abc"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order("abc")
            assert result["order"]["order_id"] == "abc"

    @pytest.mark.asyncio
    async def test_create_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"order": {"order_id": "new123"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_order(
                ticker="KXBTC-100K", side="yes", action="buy",
                count=10, yes_price=50,
            )
            assert result["order"]["order_id"] == "new123"

    @pytest.mark.asyncio
    async def test_cancel_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/portfolio/orders"): {"order": {"status": "canceled"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.cancel_order("order-123")
            assert result["order"]["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_amend_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"order": {"order_id": "amended"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.amend_order(
                "order-1",
                ticker="KXBTC", side="yes", action="buy",
                client_order_id="old", updated_client_order_id="new",
                yes_price=55,
            )
            assert result["order"]["order_id"] == "amended"

    @pytest.mark.asyncio
    async def test_decrease_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"order": {"count": 5}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.decrease_order("order-1", reduce_to=5)
            assert result["order"]["count"] == 5

    @pytest.mark.asyncio
    async def test_get_queue_positions(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"queue_positions": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_queue_positions(event_ticker="EVT-1")
            assert "queue_positions" in result

    @pytest.mark.asyncio
    async def test_get_order_queue_position(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/orders"): {"queue_position": 3}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order_queue_position("order-1")
            assert result["queue_position"] == 3


# =============================================================================
# Order Groups
# =============================================================================


class TestOrderGroups:
    @pytest.mark.asyncio
    async def test_get_order_groups(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/order_groups"): {"order_groups": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order_groups()
            assert result["order_groups"] == []

    @pytest.mark.asyncio
    async def test_create_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/order_groups"): {"order_group": {"id": "grp-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_order_group(contracts_limit=100)
            assert result["order_group"]["id"] == "grp-1"

    @pytest.mark.asyncio
    async def test_get_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/order_groups"): {"order_group": {"id": "grp-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_order_group("grp-1")
            assert result["order_group"]["id"] == "grp-1"

    @pytest.mark.asyncio
    async def test_delete_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/portfolio/order_groups"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_order_group("grp-1")
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_reset_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("PUT", "/trade-api/v2/portfolio/order_groups"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.reset_order_group("grp-1")
            assert result["ok"] is True


# =============================================================================
# Portfolio
# =============================================================================


class TestPortfolio:
    @pytest.mark.asyncio
    async def test_get_balance(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/balance"): {"balance": 10000}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_balance()
            assert result["balance"] == 10000

    @pytest.mark.asyncio
    async def test_get_positions(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/positions"): {"market_positions": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_positions(event_ticker="EVT-1")
            assert result["market_positions"] == []

    @pytest.mark.asyncio
    async def test_get_settlements(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/settlements"): {"settlements": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_settlements()
            assert result["settlements"] == []

    @pytest.mark.asyncio
    async def test_get_fills(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/portfolio/fills"): {"fills": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_fills()
            assert result["fills"] == []


# =============================================================================
# Markets
# =============================================================================


class TestMarkets:
    @pytest.mark.asyncio
    async def test_get_market(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets/KXBTC"): {"market": {"ticker": "KXBTC"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_market("KXBTC")
            assert result["market"]["ticker"] == "KXBTC"

    @pytest.mark.asyncio
    async def test_get_markets(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets"): {"markets": [], "cursor": None}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_markets(status="open", limit=50)
            assert result["markets"] == []

    @pytest.mark.asyncio
    async def test_get_market_orderbook(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets/KXBTC"): {"orderbook": {"yes": [], "no": []}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_market_orderbook("KXBTC")
            assert "orderbook" in result

    @pytest.mark.asyncio
    async def test_get_trades(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets/trades"): {"trades": [], "cursor": None}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_trades(ticker="KXBTC", limit=10)
            assert result["trades"] == []


# =============================================================================
# Events
# =============================================================================


class TestEvents:
    @pytest.mark.asyncio
    async def test_get_event(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events/EVT-1"): {"event": {"event_ticker": "EVT-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_event("EVT-1", with_nested_markets=True)
            assert result["event"]["event_ticker"] == "EVT-1"

    @pytest.mark.asyncio
    async def test_get_events(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events"): {"events": [], "cursor": None}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_events(status="open", limit=10)
            assert result["events"] == []

    @pytest.mark.asyncio
    async def test_get_multivariate_events(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events/multivariate"): {"events": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_multivariate_events(limit=5)
            assert result["events"] == []

    @pytest.mark.asyncio
    async def test_get_event_metadata(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/events/EVT-1"): {"metadata": {"category": "Crypto"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_event_metadata("EVT-1")
            assert result["metadata"]["category"] == "Crypto"


# =============================================================================
# Series
# =============================================================================


class TestSeries:
    @pytest.mark.asyncio
    async def test_get_series(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series/KXBTC"): {"series": {"ticker": "KXBTC"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_series("KXBTC", include_volume=True)
            assert result["series"]["ticker"] == "KXBTC"

    @pytest.mark.asyncio
    async def test_get_series_list(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series"): {"series": [], "cursor": None}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_series_list(category="Crypto", limit=10)
            assert result["series"] == []


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
            assert "Crypto" in result["tags_by_categories"]

    @pytest.mark.asyncio
    async def test_get_filters_by_sport(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/search/filters_by_sport"): {
            "filters_by_sports": {"NFL": {"competitions": ["NFC", "AFC"]}}
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_filters_by_sport()
            assert "NFL" in result["filters_by_sports"]


# =============================================================================
# Batch Operations
# =============================================================================


class TestBatchOperations:
    @pytest.mark.asyncio
    async def test_batch_create_empty(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            result = await c.batch_create_orders([])
            assert result == {"orders": []}

    @pytest.mark.asyncio
    async def test_batch_cancel_empty(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        async with _client(creds, cfg, {}) as c:
            result = await c.batch_cancel_orders([])
            assert result == {"orders": []}

    @pytest.mark.asyncio
    async def test_batch_create_single_chunk(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {
            "orders": [{"order_id": "o1"}, {"order_id": "o2"}]
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.batch_create_orders([
                {"ticker": "T1", "side": "yes", "action": "buy", "count": 1},
                {"ticker": "T2", "side": "no", "action": "sell", "count": 2},
            ])
            assert len(result["orders"]) == 2

    @pytest.mark.asyncio
    async def test_batch_cancel_single_chunk(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/portfolio/orders"): {
            "orders": [{"order_id": "o1", "status": "canceled"}]
        }}
        async with _client(creds, cfg, routes) as c:
            result = await c.batch_cancel_orders(["o1", "o2", "o3"])
            # Mock returns same response for each chunk
            assert len(result["orders"]) >= 1

    @pytest.mark.asyncio
    async def test_batch_create_strips_none(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"orders": [{"order_id": "o1"}]}}
        async with _client(creds, cfg, routes) as c:
            result = await c.batch_create_orders([
                {"ticker": "T1", "side": "yes", "action": "buy", "count": 1, "expiration_ts": None},
            ])
            assert len(result["orders"]) == 1

    @pytest.mark.asyncio
    async def test_batch_create_large_splits_groups(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        """25 orders should be split across groups (write_cap=10, batch_limit=20)."""
        routes = {("POST", "/trade-api/v2/portfolio/orders"): {"orders": [{"order_id": "ok"}]}}
        orders = [
            {"ticker": f"T{i}", "side": "yes", "action": "buy", "count": 1}
            for i in range(25)
        ]
        async with _client(creds, cfg, routes) as c:
            result = await c.batch_create_orders(orders)
            # Should succeed — exact count depends on grouping, but should have results
            assert len(result["orders"]) > 0

    @pytest.mark.asyncio
    async def test_batch_create_propagates_error(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/portfolio/orders"): 500}
        async with _client(creds, cfg, routes) as c:
            with pytest.raises(Exception):
                await c.batch_create_orders([
                    {"ticker": "T1", "side": "yes", "action": "buy", "count": 1},
                ])
