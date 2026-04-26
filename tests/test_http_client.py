"""Tests for pykalshi.http_client."""

import pytest

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient
from pykalshi.exceptions import KalshiAPIError, KalshiRateLimitError
from pykalshi.testing.mock_transport import make_mock_transport
from pykalshi.testing.fixtures import mock_credentials, test_config


@pytest.fixture
def creds() -> KalshiCredentials:
    return mock_credentials()


@pytest.fixture
def cfg() -> ClientConfig:
    return test_config()


class TestKalshiHttpClient:
    @pytest.mark.asyncio
    async def test_get_exchange_status(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/exchange/status"): {"exchange_active": True},
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.get_exchange_status()
            assert result["exchange_active"] is True

    @pytest.mark.asyncio
    async def test_get_market(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/markets/KXBTC"): {
                "market": {"ticker": "KXBTC", "status": "open"}
            },
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.get_market("KXBTC")
            assert result["market"]["ticker"] == "KXBTC"

    @pytest.mark.asyncio
    async def test_create_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("POST", "/trade-api/v2/portfolio/orders"): {
                "order": {"order_id": "abc123"}
            },
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.create_order(
                ticker="KXBTC-100K", side="yes", action="buy",
                count=10, yes_price=50,
            )
            assert result["order"]["order_id"] == "abc123"

    @pytest.mark.asyncio
    async def test_api_error_raised(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/exchange/status"): 500,
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            with pytest.raises(KalshiAPIError) as exc_info:
                await client.get_exchange_status()
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_429_retries_then_raises(self, creds: KalshiCredentials) -> None:
        cfg = ClientConfig(
            environment=Environment.DEMO,
            http_base_url="http://localhost:0",
            max_retries=1,
            base_retry_delay=0.01,
        )
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/exchange/status"): 429,
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            with pytest.raises(KalshiRateLimitError):
                await client.get_exchange_status()

    @pytest.mark.asyncio
    async def test_get_balance(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/portfolio/balance"): {"balance": 10000},
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.get_balance()
            assert result["balance"] == 10000

    @pytest.mark.asyncio
    async def test_get_events(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/events"): {"events": [], "cursor": None},
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.get_events(status="open", limit=10)
            assert result["events"] == []

    @pytest.mark.asyncio
    async def test_cancel_order(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({
            ("DELETE", "/trade-api/v2/portfolio/orders"): {"order": {"status": "canceled"}},
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.cancel_order("order-123")
            assert result["order"]["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_search_tags_by_categories(
        self, creds: KalshiCredentials, cfg: ClientConfig
    ) -> None:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/search/tags_by_categories"): {
                "tags_by_categories": {"Crypto": ["BTC", "ETH"]}
            },
        })
        async with KalshiHttpClient(creds, cfg, transport=transport) as client:
            result = await client.get_tags_by_categories()
            assert "Crypto" in result["tags_by_categories"]

    @pytest.mark.asyncio
    async def test_context_manager(self, creds: KalshiCredentials, cfg: ClientConfig) -> None:
        transport = make_mock_transport({})
        client = KalshiHttpClient(creds, cfg, transport=transport)
        async with client:
            pass
        # Should not raise after close
