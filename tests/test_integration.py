"""Integration tests against the Kalshi DEMO API.

These tests hit the real demo-api.kalshi.co endpoint. They require:
  - .env with KALSHI_DEMO_API_KEY_ID and KALSHI_DEMO_PRIVATE_KEY_FILE

Run with: uv run pytest tests/test_integration.py -v -m integration
Skip with: uv run pytest tests/ -v -m "not integration"
"""

import os

import pytest

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

_KEY_ID = os.environ.get("KALSHI_DEMO_API_KEY_ID", "")
_KEY_FILE = os.environ.get("KALSHI_DEMO_PRIVATE_KEY_FILE", "")
_HAS_CREDS = bool(_KEY_ID and _KEY_FILE and os.path.exists(_KEY_FILE))

pytestmark = pytest.mark.integration


def _make_client() -> KalshiHttpClient:
    creds = KalshiCredentials.from_key_file(_KEY_ID, _KEY_FILE)
    config = ClientConfig(environment=Environment.DEMO)
    return KalshiHttpClient(creds, config)


@pytest.fixture
async def client():
    c = _make_client()
    yield c
    await c.close()


# =============================================================================
# Exchange
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestExchangeIntegration:
    @pytest.mark.asyncio
    async def test_get_exchange_status(self, client: KalshiHttpClient) -> None:
        result = await client.get_exchange_status()
        assert "exchange_active" in result or "trading_active" in result

    @pytest.mark.asyncio
    async def test_get_exchange_schedule(self, client: KalshiHttpClient) -> None:
        result = await client.get_exchange_schedule()
        assert "schedule" in result


# =============================================================================
# Account
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestAccountIntegration:
    @pytest.mark.asyncio
    async def test_get_api_limits(self, client: KalshiHttpClient) -> None:
        result = await client.get_api_limits()
        # Kalshi returns rate limit info
        assert isinstance(result, dict)


# =============================================================================
# Markets
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestMarketsIntegration:
    @pytest.mark.asyncio
    async def test_get_markets(self, client: KalshiHttpClient) -> None:
        result = await client.get_markets(limit=5, status="open")
        assert "markets" in result
        assert isinstance(result["markets"], list)

    @pytest.mark.asyncio
    async def test_get_market(self, client: KalshiHttpClient) -> None:
        # First get a market ticker
        markets_resp = await client.get_markets(limit=1, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]
        result = await client.get_market(ticker)
        assert "market" in result
        assert result["market"]["ticker"] == ticker

    @pytest.mark.asyncio
    async def test_get_market_orderbook(self, client: KalshiHttpClient) -> None:
        markets_resp = await client.get_markets(limit=1, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]
        result = await client.get_market_orderbook(ticker)
        assert "orderbook" in result or "orderbook_fp" in result

    @pytest.mark.asyncio
    async def test_get_trades(self, client: KalshiHttpClient) -> None:
        result = await client.get_trades(limit=5)
        assert "trades" in result


# =============================================================================
# Events
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestEventsIntegration:
    @pytest.mark.asyncio
    async def test_get_events(self, client: KalshiHttpClient) -> None:
        result = await client.get_events(limit=5, status="open")
        assert "events" in result
        assert isinstance(result["events"], list)

    @pytest.mark.asyncio
    async def test_get_event(self, client: KalshiHttpClient) -> None:
        events_resp = await client.get_events(limit=1, status="open")
        events = events_resp.get("events", [])
        if not events:
            pytest.skip("No open events on DEMO")
        event_ticker = events[0]["event_ticker"]
        result = await client.get_event(event_ticker, with_nested_markets=True)
        assert "event" in result
        assert result["event"]["event_ticker"] == event_ticker

    @pytest.mark.asyncio
    async def test_get_multivariate_events(self, client: KalshiHttpClient) -> None:
        result = await client.get_multivariate_events(limit=5)
        # May be empty on demo but should not error
        assert isinstance(result, dict)


# =============================================================================
# Series
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestSeriesIntegration:
    @pytest.mark.asyncio
    async def test_get_series_list(self, client: KalshiHttpClient) -> None:
        result = await client.get_series_list(limit=5)
        assert "series" in result

    @pytest.mark.asyncio
    async def test_get_series(self, client: KalshiHttpClient) -> None:
        series_resp = await client.get_series_list(limit=1)
        series_list = series_resp.get("series", [])
        if not series_list:
            pytest.skip("No series on DEMO")
        ticker = series_list[0].get("ticker") or series_list[0].get("series_ticker")
        result = await client.get_series(ticker)
        assert "series" in result


# =============================================================================
# Search
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestSearchIntegration:
    @pytest.mark.asyncio
    async def test_get_tags_by_categories(self, client: KalshiHttpClient) -> None:
        result = await client.get_tags_by_categories()
        assert "tags_by_categories" in result

    @pytest.mark.asyncio
    async def test_get_filters_by_sport(self, client: KalshiHttpClient) -> None:
        result = await client.get_filters_by_sport()
        assert isinstance(result, dict)


# =============================================================================
# Portfolio (read-only)
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestPortfolioIntegration:
    @pytest.mark.asyncio
    async def test_get_balance(self, client: KalshiHttpClient) -> None:
        result = await client.get_balance()
        assert "balance" in result

    @pytest.mark.asyncio
    async def test_get_positions(self, client: KalshiHttpClient) -> None:
        result = await client.get_positions()
        assert "market_positions" in result or "positions" in result

    @pytest.mark.asyncio
    async def test_get_fills(self, client: KalshiHttpClient) -> None:
        result = await client.get_fills()
        assert "fills" in result

    @pytest.mark.asyncio
    async def test_get_orders(self, client: KalshiHttpClient) -> None:
        result = await client.get_orders(limit=5)
        assert "orders" in result
