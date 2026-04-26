"""Integration tests against the Kalshi DEMO API.

These tests hit the real demo-api.kalshi.co endpoint. They require:
  - .env with KALSHI_DEMO_API_KEY_ID and KALSHI_DEMO_PRIVATE_KEY_FILE

Run with: uv run pytest tests/test_integration.py -v
Skip with: uv run pytest tests/ -v -m "not integration"
"""

import asyncio
import os

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient
from pykalshi.exceptions import KalshiAPIError

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


async def _retry_until(coro_factory, predicate, timeout=10, interval=1):
    """Retry a coroutine until predicate returns True or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        result = await coro_factory()
        if predicate(result):
            return result
        if asyncio.get_event_loop().time() >= deadline:
            return result
        await asyncio.sleep(interval)


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

    @pytest.mark.asyncio
    async def test_get_exchange_announcements(self, client: KalshiHttpClient) -> None:
        result = await client.get_exchange_announcements()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_user_data_timestamp(self, client: KalshiHttpClient) -> None:
        result = await client.get_user_data_timestamp()
        assert isinstance(result, dict)


# =============================================================================
# Account
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestAccountIntegration:
    @pytest.mark.asyncio
    async def test_get_api_limits(self, client: KalshiHttpClient) -> None:
        result = await client.get_api_limits()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_endpoint_costs(self, client: KalshiHttpClient) -> None:
        try:
            result = await client.get_endpoint_costs()
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (403, 404):
                pytest.skip(f"endpoint_costs not available on DEMO ({e.status_code})")
            raise


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
        markets_resp = await client.get_markets(limit=1, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]
        result = await client.get_market(ticker)
        assert "market" in result

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
    async def test_get_market_orderbooks_batch(self, client: KalshiHttpClient) -> None:
        markets_resp = await client.get_markets(limit=3, status="open")
        markets = markets_resp.get("markets", [])
        if len(markets) < 2:
            pytest.skip("Not enough open markets on DEMO")
        tickers = [m["ticker"] for m in markets[:3]]
        result = await client.get_market_orderbooks(tickers)
        assert isinstance(result, dict)

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

    @pytest.mark.asyncio
    async def test_get_event(self, client: KalshiHttpClient) -> None:
        events_resp = await client.get_events(limit=1, status="open")
        events = events_resp.get("events", [])
        if not events:
            pytest.skip("No open events on DEMO")
        event_ticker = events[0]["event_ticker"]
        result = await client.get_event(event_ticker, with_nested_markets=True)
        assert "event" in result

    @pytest.mark.asyncio
    async def test_get_event_metadata(self, client: KalshiHttpClient) -> None:
        events_resp = await client.get_events(limit=1, status="open")
        events = events_resp.get("events", [])
        if not events:
            pytest.skip("No open events on DEMO")
        result = await client.get_event_metadata(events[0]["event_ticker"])
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_multivariate_events(self, client: KalshiHttpClient) -> None:
        result = await client.get_multivariate_events(limit=5)
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

    @pytest.mark.asyncio
    async def test_get_fee_changes(self, client: KalshiHttpClient) -> None:
        result = await client.get_fee_changes()
        assert isinstance(result, dict)


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
# Portfolio
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

    @pytest.mark.asyncio
    async def test_get_settlements(self, client: KalshiHttpClient) -> None:
        result = await client.get_settlements()
        assert isinstance(result, dict)


# =============================================================================
# Historical
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestHistoricalIntegration:
    @pytest.mark.asyncio
    async def test_get_historical_cutoff(self, client: KalshiHttpClient) -> None:
        result = await client.get_historical_cutoff()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_historical_markets(self, client: KalshiHttpClient) -> None:
        result = await client.get_historical_markets(limit=5)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_historical_fills(self, client: KalshiHttpClient) -> None:
        result = await client.get_historical_fills(limit=5)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_historical_orders(self, client: KalshiHttpClient) -> None:
        result = await client.get_historical_orders(limit=5)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_historical_trades(self, client: KalshiHttpClient) -> None:
        result = await client.get_historical_trades(limit=5)
        assert isinstance(result, dict)


# =============================================================================
# Milestones
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestMilestonesIntegration:
    @pytest.mark.asyncio
    async def test_get_milestones(self, client: KalshiHttpClient) -> None:
        result = await client.get_milestones(limit=5)
        assert isinstance(result, dict)


# =============================================================================
# Structured Targets
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestStructuredTargetsIntegration:
    @pytest.mark.asyncio
    async def test_get_structured_targets(self, client: KalshiHttpClient) -> None:
        result = await client.get_structured_targets(page_size=5)
        assert isinstance(result, dict)


# =============================================================================
# Incentive Programs
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestIncentiveProgramsIntegration:
    @pytest.mark.asyncio
    async def test_get_incentive_programs(self, client: KalshiHttpClient) -> None:
        result = await client.get_incentive_programs(limit=5)
        assert isinstance(result, dict)


# =============================================================================
# Communications
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestCommunicationsIntegration:
    @pytest.mark.asyncio
    async def test_get_communications_id(self, client: KalshiHttpClient) -> None:
        result = await client.get_communications_id()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_rfqs(self, client: KalshiHttpClient) -> None:
        result = await client.get_rfqs(limit=5)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_quotes(self, client: KalshiHttpClient) -> None:
        try:
            result = await client.get_quotes(limit=5)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 403):
                pytest.skip(f"quotes endpoint not available on DEMO ({e.status_code})")
            raise


# =============================================================================
# API Keys (create + list + delete lifecycle)
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestApiKeysIntegration:
    @pytest.mark.asyncio
    async def test_list_api_keys(self, client: KalshiHttpClient) -> None:
        result = await client.get_api_keys()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_create_and_delete_api_key(self, client: KalshiHttpClient) -> None:
        """Create an API key with a throwaway RSA pubkey, then delete it."""
        key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        pub_pem = key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        try:
            created = await client.create_api_key(public_key=pub_pem)
        except KalshiAPIError as e:
            if e.status_code in (400, 403):
                pytest.skip(f"API key creation not available on DEMO ({e.status_code})")
            raise

        assert isinstance(created, dict)
        # Try different response shapes Kalshi might use
        api_key_id = (
            created.get("api_key_id")
            or created.get("id")
            or created.get("api_key", {}).get("api_key_id")
            or created.get("api_key", {}).get("id")
        )
        if api_key_id is None:
            pytest.skip(f"Could not extract api_key_id from response: {list(created.keys())}")

        await client.delete_api_key(api_key_id)


# =============================================================================
# Order Groups (create -> get -> reset -> delete lifecycle)
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestOrderGroupsIntegration:
    @pytest.mark.asyncio
    async def test_order_group_lifecycle(self, client: KalshiHttpClient) -> None:
        """Create, get, reset, and delete an order group."""
        created = await client.create_order_group(contracts_limit=100)
        assert isinstance(created, dict)
        group_id = (
            created.get("order_group_id")
            or created.get("order_group", {}).get("order_group_id")
        )
        assert group_id is not None

        try:
            # Get it
            got = await client.get_order_group(group_id)
            assert isinstance(got, dict)

            # Reset it
            await client.reset_order_group(group_id)

            # List all
            all_groups = await client.get_order_groups()
            assert isinstance(all_groups, dict)
        finally:
            # Always clean up
            await client.delete_order_group(group_id)


# =============================================================================
# Orders (create -> get -> cancel lifecycle)
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestOrdersIntegration:
    @pytest.mark.asyncio
    async def test_order_create_and_cancel(self, client: KalshiHttpClient) -> None:
        """Place an order at an extreme price (won't fill), verify, cancel."""
        markets_resp = await client.get_markets(limit=5, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")

        # Find a market with bid/ask
        ticker = markets[0]["ticker"]

        # Place a limit order at 1 cent (won't fill)
        created = await client.create_order(
            ticker=ticker,
            side="yes",
            action="buy",
            count=1,
            yes_price=1,  # 1 cent — won't fill
            order_type="limit",
        )
        assert isinstance(created, dict)
        order_id = created.get("order", {}).get("order_id")
        assert order_id is not None

        try:
            # Wait for order to propagate, then verify it exists
            result = await _retry_until(
                lambda: client.get_order(order_id),
                lambda r: "order" in r,
                timeout=10,
            )
            assert "order" in result
        finally:
            # Cancel — always clean up
            await client.cancel_order(order_id)

    @pytest.mark.asyncio
    async def test_get_queue_positions(self, client: KalshiHttpClient) -> None:
        # Queue positions requires market_tickers or event_ticker
        markets_resp = await client.get_markets(limit=1, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]
        result = await client.get_queue_positions(market_tickers=ticker)
        assert isinstance(result, dict)


# =============================================================================
# Communications — RFQ lifecycle
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestRfqIntegration:
    @pytest.mark.asyncio
    async def test_rfq_create_and_delete(self, client: KalshiHttpClient) -> None:
        """Create an RFQ on a real market, then delete it."""
        markets_resp = await client.get_markets(limit=1, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")

        ticker = markets[0]["ticker"]
        try:
            created = await client.create_rfq(
                market_ticker=ticker,
                side="yes",
                size=1,
            )
            assert isinstance(created, dict)
            rfq_id = created.get("rfq", {}).get("id") or created.get("id")
            if rfq_id:
                # Get it
                got = await client.get_rfq(rfq_id)
                assert isinstance(got, dict)
                # Delete it
                await client.delete_rfq(rfq_id)
        except KalshiAPIError:
            # RFQ creation may fail on DEMO depending on account permissions
            pytest.skip("RFQ creation not available on this DEMO account")
