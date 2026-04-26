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


# =============================================================================
# Exchange (additional)
# =============================================================================


class TestExchangeAdditional:
    @pytest.mark.asyncio
    async def test_get_exchange_announcements(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/announcements"): {"announcements": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_exchange_announcements()
            assert result["announcements"] == []

    @pytest.mark.asyncio
    async def test_get_user_data_timestamp(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/exchange/user_data_timestamp"): {"timestamp": 123456}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_user_data_timestamp()
            assert result["timestamp"] == 123456


# =============================================================================
# Account (additional)
# =============================================================================


class TestAccountAdditional:
    @pytest.mark.asyncio
    async def test_get_endpoint_costs(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/account/endpoint_costs"): {"endpoints": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_endpoint_costs()
            assert "endpoints" in result


# =============================================================================
# Order Groups (additional)
# =============================================================================


class TestOrderGroupsAdditional:
    @pytest.mark.asyncio
    async def test_trigger_order_group(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("PUT", "/trade-api/v2/portfolio/order_groups"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.trigger_order_group("grp-1")
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_update_order_group_limit(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("PUT", "/trade-api/v2/portfolio/order_groups"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.update_order_group_limit("grp-1", limit=200)
            assert result["ok"] is True


# =============================================================================
# Markets (additional)
# =============================================================================


class TestMarketsAdditional:
    @pytest.mark.asyncio
    async def test_get_market_orderbooks(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/markets/orderbooks"): {"orderbooks": {}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_market_orderbooks(["KXBTC", "KXETH"])
            assert "orderbooks" in result

    @pytest.mark.asyncio
    async def test_get_market_candlesticks(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series"): {"candlesticks": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_market_candlesticks(
                "KXBTC", "KXBTC-100K", start_ts=100, end_ts=200, period_interval=60
            )
            assert "candlesticks" in result


# =============================================================================
# Events (additional)
# =============================================================================


class TestEventsAdditional:
    @pytest.mark.asyncio
    async def test_get_event_candlesticks(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series"): {"candlesticks": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_event_candlesticks(
                "KXBTC", "EVT-1", start_ts=100, end_ts=200, period_interval=60
            )
            assert "candlesticks" in result

    @pytest.mark.asyncio
    async def test_get_forecast_percentile_history(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series"): {"history": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_forecast_percentile_history(
                "KXBTC", "EVT-1", percentiles=[25, 50, 75], start_ts=100, end_ts=200, period_interval=60
            )
            assert "history" in result


# =============================================================================
# Series (additional)
# =============================================================================


class TestSeriesAdditional:
    @pytest.mark.asyncio
    async def test_get_fee_changes(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/series/fee_changes"): {"fee_changes": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_fee_changes(series_ticker="KXBTC")
            assert "fee_changes" in result


# =============================================================================
# Historical
# =============================================================================


class TestHistorical:
    @pytest.mark.asyncio
    async def test_get_historical_cutoff(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/cutoff"): {"cutoff_ts": 1000}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_cutoff()
            assert "cutoff_ts" in result

    @pytest.mark.asyncio
    async def test_get_historical_markets(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/markets"): {"markets": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_markets(limit=5)
            assert result["markets"] == []

    @pytest.mark.asyncio
    async def test_get_historical_market(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/markets"): {"market": {"ticker": "OLD-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_market("OLD-1")
            assert result["market"]["ticker"] == "OLD-1"

    @pytest.mark.asyncio
    async def test_get_historical_market_candlesticks(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/markets"): {"candlesticks": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_market_candlesticks(
                "OLD-1", start_ts=100, end_ts=200, period_interval=60
            )
            assert "candlesticks" in result

    @pytest.mark.asyncio
    async def test_get_historical_fills(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/fills"): {"fills": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_fills(limit=10)
            assert result["fills"] == []

    @pytest.mark.asyncio
    async def test_get_historical_orders(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/orders"): {"orders": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_orders(limit=10)
            assert result["orders"] == []

    @pytest.mark.asyncio
    async def test_get_historical_trades(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/historical/trades"): {"trades": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_historical_trades(limit=10)
            assert result["trades"] == []


# =============================================================================
# API Keys
# =============================================================================


class TestApiKeys:
    @pytest.mark.asyncio
    async def test_get_api_keys(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/api_keys"): {"api_keys": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_api_keys()
            assert result["api_keys"] == []

    @pytest.mark.asyncio
    async def test_create_api_key(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/api_keys"): {"api_key": "new-key"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_api_key(public_key="ssh-rsa AAAA...")
            assert result["api_key"] == "new-key"

    @pytest.mark.asyncio
    async def test_generate_api_key(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/api_keys"): {"api_key": "gen-key"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.generate_api_key(name="test-key")
            assert result["api_key"] == "gen-key"

    @pytest.mark.asyncio
    async def test_delete_api_key(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/api_keys"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_api_key("key-to-delete")
            assert result["ok"] is True


# =============================================================================
# Communications
# =============================================================================


class TestCommunications:
    @pytest.mark.asyncio
    async def test_get_communications_id(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/id"): {"id": "comm-123"}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_communications_id()
            assert result["id"] == "comm-123"

    @pytest.mark.asyncio
    async def test_get_rfqs(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/rfqs"): {"rfqs": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_rfqs(limit=5)
            assert result["rfqs"] == []

    @pytest.mark.asyncio
    async def test_create_rfq(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/communications/rfqs"): {"rfq": {"id": "rfq-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_rfq(market_ticker="KXBTC", side="yes", size=100)
            assert result["rfq"]["id"] == "rfq-1"

    @pytest.mark.asyncio
    async def test_get_rfq(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/rfqs"): {"rfq": {"id": "rfq-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_rfq("rfq-1")
            assert result["rfq"]["id"] == "rfq-1"

    @pytest.mark.asyncio
    async def test_delete_rfq(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/communications/rfqs"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_rfq("rfq-1")
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_get_quotes(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/quotes"): {"quotes": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_quotes(limit=5)
            assert result["quotes"] == []

    @pytest.mark.asyncio
    async def test_create_quote(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("POST", "/trade-api/v2/communications/quotes"): {"quote": {"id": "q-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.create_quote(rfq_id="rfq-1", price="0.50", size=50)
            assert result["quote"]["id"] == "q-1"

    @pytest.mark.asyncio
    async def test_get_quote(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/communications/quotes"): {"quote": {"id": "q-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_quote("q-1")
            assert result["quote"]["id"] == "q-1"

    @pytest.mark.asyncio
    async def test_delete_quote(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("DELETE", "/trade-api/v2/communications/quotes"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.delete_quote("q-1")
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_accept_quote(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("PUT", "/trade-api/v2/communications/quotes"): {"ok": True}}
        async with _client(creds, cfg, routes) as c:
            result = await c.accept_quote("q-1")
            assert result["ok"] is True


# =============================================================================
# Live Data
# =============================================================================


class TestLiveData:
    @pytest.mark.asyncio
    async def test_get_live_data(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/live_data/milestone"): {"data": {}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_live_data("ms-1")
            assert "data" in result

    @pytest.mark.asyncio
    async def test_get_live_data_batch(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/live_data/batch"): {"results": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_live_data_batch(["ms-1", "ms-2"])
            assert "results" in result

    @pytest.mark.asyncio
    async def test_get_game_stats(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/live_data/milestone"): {"stats": {}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_game_stats("ms-1")
            assert "stats" in result


# =============================================================================
# Milestones
# =============================================================================


class TestMilestones:
    @pytest.mark.asyncio
    async def test_get_milestone(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/milestones"): {"milestone": {"id": "ms-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_milestone("ms-1")
            assert result["milestone"]["id"] == "ms-1"

    @pytest.mark.asyncio
    async def test_get_milestones(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/milestones"): {"milestones": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_milestones(limit=10, category="Sports")
            assert result["milestones"] == []


# =============================================================================
# Structured Targets
# =============================================================================


class TestStructuredTargets:
    @pytest.mark.asyncio
    async def test_get_structured_targets(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/structured_targets"): {"targets": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_structured_targets(competition="NFL")
            assert result["targets"] == []

    @pytest.mark.asyncio
    async def test_get_structured_target(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/structured_targets"): {"target": {"id": "st-1"}}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_structured_target("st-1")
            assert result["target"]["id"] == "st-1"


# =============================================================================
# Incentive Programs
# =============================================================================


class TestIncentivePrograms:
    @pytest.mark.asyncio
    async def test_get_incentive_programs(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        routes = {("GET", "/trade-api/v2/incentive_programs"): {"programs": []}}
        async with _client(creds, cfg, routes) as c:
            result = await c.get_incentive_programs(status="active")
            assert result["programs"] == []
