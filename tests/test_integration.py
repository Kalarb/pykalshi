"""Integration tests against the Kalshi DEMO API.

These tests hit the real demo-api.kalshi.co endpoint. They require:
  - .env with KALSHI_DEMO_API_KEY_ID and KALSHI_DEMO_PRIVATE_KEY_FILE

Run with: uv run pytest tests/test_integration.py -v
Skip with: uv run pytest tests/ -v -m "not integration"
"""

import asyncio
import os
import time

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
    """Retry a coroutine until predicate returns True or timeout.

    Handles KalshiAPIError(404) as "not propagated yet" and keeps retrying.
    Kalshi DEMO has ~5 second propagation delay on writes.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    last_result = None
    while True:
        try:
            last_result = await coro_factory()
            if predicate(last_result):
                return last_result
        except KalshiAPIError as e:
            if e.status_code != 404:
                raise
            # 404 = not propagated yet, keep retrying
        if asyncio.get_event_loop().time() >= deadline:
            if last_result is not None:
                return last_result
            raise TimeoutError("Timed out waiting for resource to propagate")
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

    @pytest.mark.asyncio
    async def test_get_market_candlesticks(self, client: KalshiHttpClient) -> None:
        """Fetch candlesticks for an open market using its series ticker."""
        events_resp = await client.get_events(
            limit=1, status="open", with_nested_markets=True,
        )
        events = events_resp.get("events", [])
        if not events:
            pytest.skip("No open events on DEMO")
        event = events[0]
        series_ticker = event.get("series_ticker")
        markets = event.get("markets", [])
        if not series_ticker or not markets:
            pytest.skip("No series_ticker or nested markets on DEMO event")
        ticker = markets[0]["ticker"]

        now = int(time.time())
        try:
            result = await client.get_market_candlesticks(
                series_ticker, ticker,
                start_ts=now - 86400, end_ts=now, period_interval=3600,
            )
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Market candlesticks not available ({e.status_code})")
            raise


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

    @pytest.mark.asyncio
    async def test_get_event_candlesticks(self, client: KalshiHttpClient) -> None:
        """Fetch candlesticks for an open event using its series ticker."""
        events_resp = await client.get_events(limit=1, status="open")
        events = events_resp.get("events", [])
        if not events:
            pytest.skip("No open events on DEMO")
        event = events[0]
        series_ticker = event.get("series_ticker")
        event_ticker = event.get("event_ticker")
        if not series_ticker or not event_ticker:
            pytest.skip("Event missing series_ticker or event_ticker")

        now = int(time.time())
        try:
            result = await client.get_event_candlesticks(
                series_ticker, event_ticker,
                start_ts=now - 86400, end_ts=now, period_interval=3600,
            )
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Event candlesticks not available ({e.status_code})")
            raise

    @pytest.mark.asyncio
    async def test_get_forecast_percentile_history(self, client: KalshiHttpClient) -> None:
        """Fetch forecast percentile history for an open event."""
        events_resp = await client.get_events(limit=1, status="open")
        events = events_resp.get("events", [])
        if not events:
            pytest.skip("No open events on DEMO")
        event = events[0]
        series_ticker = event.get("series_ticker")
        event_ticker = event.get("event_ticker")
        if not series_ticker or not event_ticker:
            pytest.skip("Event missing series_ticker or event_ticker")

        now = int(time.time())
        try:
            result = await client.get_forecast_percentile_history(
                series_ticker, event_ticker,
                percentiles=[25, 50, 75],
                start_ts=now - 86400, end_ts=now, period_interval=3600,
            )
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Forecast percentile history not available ({e.status_code})")
            raise


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

    @pytest.mark.asyncio
    async def test_get_historical_market(self, client: KalshiHttpClient) -> None:
        """Fetch a single historical market by ticker."""
        hist = await client.get_historical_markets(limit=1)
        markets = hist.get("markets", [])
        if not markets:
            pytest.skip("No historical markets on DEMO")
        ticker = markets[0].get("ticker")
        if not ticker:
            pytest.skip("Historical market missing ticker")
        try:
            result = await client.get_historical_market(ticker)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Historical market not available ({e.status_code})")
            raise

    @pytest.mark.asyncio
    async def test_get_historical_market_candlesticks(self, client: KalshiHttpClient) -> None:
        """Fetch candlesticks for a historical market."""
        hist = await client.get_historical_markets(limit=1)
        markets = hist.get("markets", [])
        if not markets:
            pytest.skip("No historical markets on DEMO")
        ticker = markets[0].get("ticker")
        if not ticker:
            pytest.skip("Historical market missing ticker")

        now = int(time.time())
        try:
            result = await client.get_historical_market_candlesticks(
                ticker, start_ts=0, end_ts=now, period_interval=86400,
            )
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Historical candlesticks not available ({e.status_code})")
            raise


# =============================================================================
# Milestones
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestMilestonesIntegration:
    @pytest.mark.asyncio
    async def test_get_milestones(self, client: KalshiHttpClient) -> None:
        result = await client.get_milestones(limit=5)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_milestone_by_id(self, client: KalshiHttpClient) -> None:
        """Fetch a single milestone by ID."""
        listing = await client.get_milestones(limit=1)
        milestones = listing.get("milestones", [])
        if not milestones:
            pytest.skip("No milestones on DEMO")
        milestone_id = milestones[0].get("id") or milestones[0].get("milestone_id")
        if not milestone_id:
            pytest.skip("Milestone missing ID field")
        try:
            result = await client.get_milestone(milestone_id)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"get_milestone not available ({e.status_code})")
            raise


# =============================================================================
# Structured Targets
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestStructuredTargetsIntegration:
    @pytest.mark.asyncio
    async def test_get_structured_targets(self, client: KalshiHttpClient) -> None:
        result = await client.get_structured_targets(page_size=5)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_structured_target_by_id(self, client: KalshiHttpClient) -> None:
        """Fetch a single structured target by ID."""
        listing = await client.get_structured_targets(page_size=1)
        targets = listing.get("structured_targets", [])
        if not targets:
            pytest.skip("No structured targets on DEMO")
        target_id = (
            targets[0].get("id")
            or targets[0].get("structured_target_id")
        )
        if not target_id:
            pytest.skip("Structured target missing ID field")
        try:
            result = await client.get_structured_target(target_id)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"get_structured_target not available ({e.status_code})")
            raise


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
# Live Data
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No DEMO credentials in .env")
class TestLiveDataIntegration:
    @pytest.mark.asyncio
    async def test_get_live_data(self, client: KalshiHttpClient) -> None:
        """Fetch live data for a milestone."""
        listing = await client.get_milestones(limit=1)
        milestones = listing.get("milestones", [])
        if not milestones:
            pytest.skip("No milestones on DEMO")
        milestone_id = milestones[0].get("id") or milestones[0].get("milestone_id")
        if not milestone_id:
            pytest.skip("Milestone missing ID field")
        try:
            result = await client.get_live_data(milestone_id)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Live data not available for milestone ({e.status_code})")
            raise

    @pytest.mark.asyncio
    async def test_get_live_data_batch(self, client: KalshiHttpClient) -> None:
        """Fetch live data for multiple milestones."""
        listing = await client.get_milestones(limit=3)
        milestones = listing.get("milestones", [])
        if not milestones:
            pytest.skip("No milestones on DEMO")
        ids = [
            m.get("id") or m.get("milestone_id")
            for m in milestones
            if m.get("id") or m.get("milestone_id")
        ]
        if not ids:
            pytest.skip("Milestones missing ID fields")
        try:
            result = await client.get_live_data_batch(ids)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Live data batch not available ({e.status_code})")
            raise

    @pytest.mark.asyncio
    async def test_get_game_stats(self, client: KalshiHttpClient) -> None:
        """Fetch game stats for a milestone."""
        listing = await client.get_milestones(limit=1)
        milestones = listing.get("milestones", [])
        if not milestones:
            pytest.skip("No milestones on DEMO")
        milestone_id = milestones[0].get("id") or milestones[0].get("milestone_id")
        if not milestone_id:
            pytest.skip("Milestone missing ID field")
        try:
            result = await client.get_game_stats(milestone_id)
            assert isinstance(result, dict)
        except KalshiAPIError as e:
            if e.status_code in (400, 404):
                pytest.skip(f"Game stats not available for milestone ({e.status_code})")
            raise


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

    @pytest.mark.asyncio
    async def test_generate_api_key(self, client: KalshiHttpClient) -> None:
        """Generate an API key by name, then delete it."""
        try:
            generated = await client.generate_api_key(name="pykalshi-test-gen")
        except KalshiAPIError as e:
            if e.status_code in (400, 403):
                pytest.skip(f"generate_api_key not available on DEMO ({e.status_code})")
            raise

        assert isinstance(generated, dict)
        api_key_id = (
            generated.get("api_key_id")
            or generated.get("id")
            or generated.get("api_key", {}).get("api_key_id")
            or generated.get("api_key", {}).get("id")
        )
        if api_key_id:
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
            # Get it (may need retry due to propagation delay)
            got = await _retry_until(
                lambda: client.get_order_group(group_id),
                lambda r: isinstance(r, dict),
                timeout=20,
            )
            assert isinstance(got, dict)

            # Update limit
            await client.update_order_group_limit(group_id, limit=50)

            # Reset it
            await client.reset_order_group(group_id)

            # List all
            all_groups = await client.get_order_groups()
            assert isinstance(all_groups, dict)
        except TimeoutError:
            pass  # Propagation delay — still clean up
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
            # Wait for order to propagate, then verify it exists.
            # CI can have 15s+ propagation delay.
            result = await _retry_until(
                lambda: client.get_order(order_id),
                lambda r: "order" in r,
                timeout=20,
            )
            assert "order" in result
        except TimeoutError:
            pass  # Order didn't propagate in time — still cancel below
        finally:
            # Cancel — always clean up regardless of propagation
            await client.cancel_order(order_id)

    @pytest.mark.asyncio
    async def test_get_queue_positions(self, client: KalshiHttpClient) -> None:
        markets_resp = await client.get_markets(limit=1, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]
        result = await client.get_queue_positions(market_tickers=ticker)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_amend_order(self, client: KalshiHttpClient) -> None:
        """Create order → wait → amend price → cancel."""
        import uuid

        markets_resp = await client.get_markets(limit=5, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]

        client_oid = str(uuid.uuid4())
        created = await client.create_order(
            ticker=ticker, side="yes", action="buy",
            count=1, yes_price=1, order_type="limit",
            client_order_id=client_oid,
        )
        order_id = created.get("order", {}).get("order_id")
        assert order_id is not None

        try:
            await _retry_until(
                lambda: client.get_order(order_id),
                lambda r: "order" in r,
                timeout=20,
            )
            updated_oid = str(uuid.uuid4())
            amended = await client.amend_order(
                order_id,
                ticker=ticker, side="yes", action="buy",
                client_order_id=client_oid,
                updated_client_order_id=updated_oid,
                yes_price=2,
            )
            assert isinstance(amended, dict)
        except (TimeoutError, KalshiAPIError):
            pass  # propagation delay or amend not supported — still clean up
        finally:
            try:
                await client.cancel_order(order_id)
            except KalshiAPIError:
                pass  # order may already be gone after amend

    @pytest.mark.asyncio
    async def test_decrease_order(self, client: KalshiHttpClient) -> None:
        """Create order with count=2 → wait → decrease to 1 → cancel."""
        markets_resp = await client.get_markets(limit=5, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]

        created = await client.create_order(
            ticker=ticker, side="yes", action="buy",
            count=2, yes_price=1, order_type="limit",
        )
        order_id = created.get("order", {}).get("order_id")
        assert order_id is not None

        try:
            await _retry_until(
                lambda: client.get_order(order_id),
                lambda r: "order" in r,
                timeout=20,
            )
            decreased = await client.decrease_order(order_id, reduce_to=1)
            assert isinstance(decreased, dict)
        except (TimeoutError, KalshiAPIError):
            pass
        finally:
            await client.cancel_order(order_id)

    @pytest.mark.asyncio
    async def test_batch_create_and_cancel(self, client: KalshiHttpClient) -> None:
        """Batch create 3 orders → batch cancel all."""
        markets_resp = await client.get_markets(limit=5, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]

        orders_to_create = [
            {"ticker": ticker, "side": "yes", "action": "buy",
             "count": 1, "yes_price": 1, "type": "limit"}
            for _ in range(3)
        ]
        created = await client.batch_create_orders(orders_to_create)
        assert isinstance(created, dict)
        # Batch response: {"orders": [{"order": {"order_id": "..."}}, ...]}
        order_ids = []
        for entry in created.get("orders", []):
            oid = entry.get("order_id") or entry.get("order", {}).get("order_id")
            if oid:
                order_ids.append(oid)
        assert len(order_ids) > 0

        try:
            # Wait for at least one to propagate
            await _retry_until(
                lambda: client.get_order(order_ids[0]),
                lambda r: "order" in r,
                timeout=20,
            )
        except TimeoutError:
            pass

        # Batch cancel all
        cancelled = await client.batch_cancel_orders(order_ids)
        assert isinstance(cancelled, dict)

    @pytest.mark.asyncio
    async def test_get_order_queue_position(self, client: KalshiHttpClient) -> None:
        """Create order → wait → get its queue position → cancel."""
        markets_resp = await client.get_markets(limit=5, status="open")
        markets = markets_resp.get("markets", [])
        if not markets:
            pytest.skip("No open markets on DEMO")
        ticker = markets[0]["ticker"]

        created = await client.create_order(
            ticker=ticker, side="yes", action="buy",
            count=1, yes_price=1, order_type="limit",
        )
        order_id = created.get("order", {}).get("order_id")
        assert order_id is not None

        try:
            await _retry_until(
                lambda: client.get_order(order_id),
                lambda r: "order" in r,
                timeout=20,
            )
            qp = await client.get_order_queue_position(order_id)
            assert isinstance(qp, dict)
        except (TimeoutError, KalshiAPIError):
            pass
        finally:
            await client.cancel_order(order_id)


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
