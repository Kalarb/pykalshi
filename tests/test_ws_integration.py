"""WebSocket integration tests against Kalshi PROD API.

Uses PROD because WS channels are read-only (no orders placed).
Tests subscribe to KXBTC15M (recurring 15-min BTC) and KXBTCD (BTC daily)
which always have active markets with reliable orderbook/ticker/trade activity.

Run with: uv run pytest tests/test_ws_integration.py -v
"""

import asyncio
import os

import orjson
import pytest

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment
from pykalshi.http_client import KalshiHttpClient
from pykalshi.ws_client import KalshiWebSocketClient

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

_KEY_ID = os.environ.get("KALSHI_PROD_READ_ONLY_API_KEY_ID", "")
_KEY_FILE = os.environ.get("KALSHI_PROD_READ_ONLY_PRIVATE_KEY_FILE", "")
_HAS_CREDS = bool(_KEY_ID and _KEY_FILE and os.path.exists(_KEY_FILE))

pytestmark = pytest.mark.integration


class MessageCollector:
    """Callback that collects WS messages into a list."""

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.raw: list[str] = []

    async def __call__(self, msg: str) -> None:
        self.raw.append(msg)
        try:
            self.messages.append(orjson.loads(msg))
        except orjson.JSONDecodeError:
            pass

    def of_type(self, msg_type: str) -> list[dict]:
        return [m for m in self.messages if m.get("type") == msg_type]

    def with_ticker(self, ticker: str) -> list[dict]:
        return [
            m for m in self.messages
            if m.get("msg", {}).get("market_ticker") == ticker
        ]

    async def wait_for_type(self, msg_type: str, timeout: float = 15.0) -> dict:
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            matches = self.of_type(msg_type)
            if matches:
                return matches[0]
            await asyncio.sleep(0.1)
        raise TimeoutError(f"No {msg_type} message within {timeout}s")

    async def wait_for_subscribed(self, timeout: float = 10.0) -> dict:
        return await self.wait_for_type("subscribed", timeout)


def _make_http_client() -> KalshiHttpClient:
    creds = KalshiCredentials.from_key_file(_KEY_ID, _KEY_FILE)
    return KalshiHttpClient(creds, ClientConfig(environment=Environment.PROD))


def _make_ws_client(collector: MessageCollector) -> KalshiWebSocketClient:
    creds = KalshiCredentials.from_key_file(_KEY_ID, _KEY_FILE)
    return KalshiWebSocketClient(
        creds,
        ClientConfig(environment=Environment.PROD),
        on_message_callback=collector,
    )


async def _get_btc15m_ticker(http: KalshiHttpClient) -> str:
    result = await http.get_events(
        status="open", series_ticker="KXBTC15M",
        with_nested_markets=True, limit=1,
    )
    if not result.events or not result.events[0].markets:
        pytest.skip("No open KXBTC15M events on PROD")
    return result.events[0].markets[0].ticker


async def _get_btcd_ticker(http: KalshiHttpClient) -> str:
    result = await http.get_events(
        status="open", series_ticker="KXBTCD",
        with_nested_markets=True, limit=1,
    )
    if not result.events or not result.events[0].markets:
        pytest.skip("No open KXBTCD events on PROD")
    return result.events[0].markets[0].ticker


# =============================================================================
# Data channels — subscribe + receive data
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No PROD credentials in .env")
class TestWsDataChannels:
    @pytest.mark.asyncio
    async def test_ws_connect_and_receive_orderbook(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["orderbook_delta"])
            snapshot = await collector.wait_for_type("orderbook_snapshot", timeout=15)
            assert snapshot["msg"]["market_ticker"] == ticker
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_receive_ticker(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["ticker"])
            try:
                msg = await collector.wait_for_type("ticker", timeout=60)
                assert msg["msg"]["market_ticker"] == ticker
            except TimeoutError:
                pytest.skip("No ticker message within 60s — market may be between windows")
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_receive_trade(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["trade"])
            try:
                msg = await collector.wait_for_type("trade", timeout=60)
                assert msg["msg"]["market_ticker"] == ticker
            except TimeoutError:
                pytest.skip("No trade within 60s — market may be quiet")
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_multi_channel_subscribe(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["orderbook_delta", "ticker"])
            # Wait for both types
            await collector.wait_for_type("orderbook_snapshot", timeout=15)
            await collector.wait_for_type("ticker", timeout=30)
            assert len(collector.of_type("orderbook_snapshot")) >= 1
            assert len(collector.of_type("ticker")) >= 1
        finally:
            await ws.unsubscribe_all()
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_subscribe_market_lifecycle(self) -> None:
        """Subscribe to market_lifecycle_v2 and wait for a message (may be flaky)."""
        collector = MessageCollector()
        ws = _make_ws_client(collector)
        try:
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            # market_lifecycle_v2 is global — no market ticker needed
            ws.channels["market_lifecycle_v2"] = __import__(
                "pykalshi.ws_client", fromlist=["ChannelState"]
            ).ChannelState(name="market_lifecycle_v2")
            await ws._send_subscribe("market_lifecycle_v2", [])
            # Wait for subscribed confirmation
            await collector.wait_for_subscribed(timeout=10)
            # Try to receive a lifecycle message (flaky — depends on market activity)
            try:
                msg = await collector.wait_for_type("market_lifecycle_v2", timeout=60)
                assert "market_ticker" in msg.get("msg", {})
            except TimeoutError:
                pass  # Expected — no market lifecycle events during test window
        finally:
            await ws.close()


# =============================================================================
# Subscribe-only channels (verify SID)
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No PROD credentials in .env")
class TestWsSubscribeOnly:
    """Channels where we verify subscription succeeds (SID returned) but may not get data."""

    @pytest.mark.asyncio
    async def test_ws_subscribe_fill(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["fill"])
            await collector.wait_for_subscribed(timeout=10)
            assert "fill" in ws.channels
            assert ws.channels["fill"].sid is not None
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_subscribe_market_positions(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["market_positions"])
            await collector.wait_for_subscribed(timeout=10)
            assert "market_positions" in ws.channels
            assert ws.channels["market_positions"].sid is not None
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_subscribe_user_orders(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            await ws.add_market(ticker, ["user_orders"])
            await collector.wait_for_subscribed(timeout=10)
            assert "user_orders" in ws.channels
            assert ws.channels["user_orders"].sid is not None
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_subscribe_communications(self) -> None:
        collector = MessageCollector()
        ws = _make_ws_client(collector)
        try:
            await ws.connect()
            asyncio.create_task(ws.listener_loop())
            from pykalshi.ws_client import ChannelState
            ws.channels["communications"] = ChannelState(name="communications")
            await ws._send_subscribe("communications", [])
            await collector.wait_for_subscribed(timeout=10)
            assert "communications" in ws.channels
        finally:
            await ws.close()


# =============================================================================
# Subscription management operations
# =============================================================================


@pytest.mark.skipif(not _HAS_CREDS, reason="No PROD credentials in .env")
class TestWsSubscriptionOps:
    @pytest.mark.asyncio
    async def test_ws_add_market(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            btc15m = await _get_btc15m_ticker(http)
            btcd = await _get_btcd_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())

            # Subscribe with BTC15M only
            await ws.add_market(btc15m, ["orderbook_delta"])
            snapshot1 = await collector.wait_for_type("orderbook_snapshot", timeout=15)
            assert snapshot1["msg"]["market_ticker"] == btc15m

            # Add BTCD market
            await ws.add_market(btcd, ["orderbook_delta"])
            # Wait for BTCD snapshot
            deadline = asyncio.get_event_loop().time() + 15
            while asyncio.get_event_loop().time() < deadline:
                btcd_snapshots = [
                    m for m in collector.of_type("orderbook_snapshot")
                    if m.get("msg", {}).get("market_ticker") == btcd
                ]
                if btcd_snapshots:
                    break
                await asyncio.sleep(0.1)
            assert len(btcd_snapshots) >= 1
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_remove_market(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            btc15m = await _get_btc15m_ticker(http)
            btcd = await _get_btcd_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())

            # Subscribe to both
            await ws.add_markets([btc15m, btcd], ["orderbook_delta"])
            await asyncio.sleep(3)  # let snapshots arrive

            # Remove BTCD
            await ws.remove_market(btcd, ["orderbook_delta"])
            collector.messages.clear()  # reset after removal

            # Collect for 3s — should only see BTC15M messages
            await asyncio.sleep(3)
            btcd_msgs = collector.with_ticker(btcd)
            assert len(btcd_msgs) == 0, f"Got {len(btcd_msgs)} messages for removed market"
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_unsubscribe_all(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())

            await ws.add_market(ticker, ["orderbook_delta", "ticker"])
            await asyncio.sleep(2)  # let some messages arrive

            await ws.unsubscribe_all()
            # Give server time to process unsubscribe before clearing
            await asyncio.sleep(1)
            collector.messages.clear()

            # Wait 3s — should get no (or very few residual) data messages
            await asyncio.sleep(3)
            data_msgs = [
                m for m in collector.messages
                if m.get("type") in (
                    "orderbook_snapshot", "orderbook_delta", "ticker", "trade"
                )
            ]
            # Tolerate up to 3 residual in-flight messages
            assert len(data_msgs) <= 3, f"Got {len(data_msgs)} data messages after unsubscribe_all"
        finally:
            await ws.close()
            await http.close()

    @pytest.mark.asyncio
    async def test_ws_request_snapshot(self) -> None:
        collector = MessageCollector()
        http = _make_http_client()
        ws = _make_ws_client(collector)
        try:
            ticker = await _get_btc15m_ticker(http)
            await ws.connect()
            asyncio.create_task(ws.listener_loop())

            await ws.add_market(ticker, ["orderbook_delta"])
            await collector.wait_for_type("orderbook_snapshot", timeout=15)
            initial_count = len(collector.of_type("orderbook_snapshot"))

            # Request a second snapshot
            await ws.request_snapshot([ticker])
            deadline = asyncio.get_event_loop().time() + 15
            while asyncio.get_event_loop().time() < deadline:
                if len(collector.of_type("orderbook_snapshot")) > initial_count:
                    break
                await asyncio.sleep(0.1)

            assert len(collector.of_type("orderbook_snapshot")) > initial_count
        finally:
            await ws.close()
            await http.close()
