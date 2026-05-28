"""Tests for pykalshi.ws_client — message routing and channel mapping."""

import asyncio

import orjson
import pytest

from pykalshi.exceptions import KalshiSequenceGapError
from pykalshi.ws_client import MSG_TYPE_TO_CHANNEL, ChannelState, KalshiWebSocketClient
from pykalshi.testing.fixtures import mock_credentials, test_config as _test_config


# =============================================================================
# MSG_TYPE_TO_CHANNEL completeness (validated against AsyncAPI spec)
# =============================================================================

# All message types defined in the Kalshi AsyncAPI 3.0 spec
ASYNCAPI_MESSAGE_TYPES = {
    # orderbook_delta channel
    "orderbook_snapshot",
    "orderbook_delta",
    # ticker channel
    "ticker",
    # trade channel
    "trade",
    # fill channel
    "fill",
    # market_positions channel
    "market_position",
    # market_lifecycle_v2 channel
    "market_lifecycle_v2",
    "event_lifecycle",  # also on multivariate_market_lifecycle
    "event_fee_update",
    # multivariate_market_lifecycle channel
    "multivariate_market_lifecycle",
    # multivariate channel
    "multivariate_lookup",
    # communications channel
    "rfq_created",
    "rfq_deleted",
    "quote_created",
    "quote_accepted",
    "quote_executed",
    # order_group_updates channel
    "order_group_updates",
    # user_orders channel
    "user_order",
}

# All subscribable channels from the AsyncAPI spec
ASYNCAPI_CHANNELS = {
    "orderbook_delta",
    "ticker",
    "trade",
    "fill",
    "market_positions",
    "market_lifecycle_v2",
    "multivariate_market_lifecycle",
    "multivariate",
    "communications",
    "order_group_updates",
    "user_orders",
}


class TestMsgTypeToChannel:
    def test_covers_all_asyncapi_message_types(self) -> None:
        """Every message type from the AsyncAPI spec must be in our mapping."""
        missing = ASYNCAPI_MESSAGE_TYPES - set(MSG_TYPE_TO_CHANNEL.keys())
        assert missing == set(), f"Missing message types: {missing}"

    def test_no_extra_message_types(self) -> None:
        """Our mapping should not contain types not in the spec."""
        extra = set(MSG_TYPE_TO_CHANNEL.keys()) - ASYNCAPI_MESSAGE_TYPES
        assert extra == set(), f"Extra message types not in spec: {extra}"

    def test_all_channels_referenced(self) -> None:
        """Every channel from the spec should be a value in our mapping."""
        mapped_channels = {v for v in MSG_TYPE_TO_CHANNEL.values() if v is not None}
        missing = ASYNCAPI_CHANNELS - mapped_channels
        assert missing == set(), f"Channels not referenced by any message type: {missing}"

    def test_event_lifecycle_is_multi_channel(self) -> None:
        """event_lifecycle arrives on multiple channels, so mapped to None."""
        assert MSG_TYPE_TO_CHANNEL["event_lifecycle"] is None

    def test_orderbook_types_map_to_orderbook_delta(self) -> None:
        assert MSG_TYPE_TO_CHANNEL["orderbook_snapshot"] == "orderbook_delta"
        assert MSG_TYPE_TO_CHANNEL["orderbook_delta"] == "orderbook_delta"

    def test_communications_types(self) -> None:
        for msg_type in ["rfq_created", "rfq_deleted", "quote_created", "quote_accepted", "quote_executed"]:
            assert MSG_TYPE_TO_CHANNEL[msg_type] == "communications"

    def test_user_order_maps_to_user_orders(self) -> None:
        assert MSG_TYPE_TO_CHANNEL["user_order"] == "user_orders"

    def test_order_group_updates_maps_correctly(self) -> None:
        assert MSG_TYPE_TO_CHANNEL["order_group_updates"] == "order_group_updates"


# =============================================================================
# Message routing in _handle_incoming_message
# =============================================================================


class TestMessageRouting:
    """Test that _handle_incoming_message correctly processes different message types."""

    def _make_client(self) -> KalshiWebSocketClient:
        creds = mock_credentials()
        cfg = _test_config()
        return KalshiWebSocketClient(creds, cfg)

    def _setup_channel(self, client: KalshiWebSocketClient, channel: str, sid: int) -> None:
        """Simulate a subscribed channel with a known SID."""
        state = ChannelState(name=channel)
        state.sid = sid
        state.seq = 0
        client.channels[channel] = state
        client._sid_map[sid] = state

    @pytest.mark.asyncio
    async def test_orderbook_snapshot_updates_seq(self) -> None:
        client = self._make_client()
        self._setup_channel(client, "orderbook_delta", sid=1)
        msg = orjson.dumps({
            "type": "orderbook_snapshot",
            "sid": 1,
            "seq": 1,
            "msg": {"market_ticker": "TEST-1", "market_id": "uuid"},
        })
        await client._handle_incoming_message(msg)
        assert client._sid_map[1].seq == 1

    @pytest.mark.asyncio
    async def test_ticker_updates_seq(self) -> None:
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=2)
        msg = orjson.dumps({"type": "ticker", "sid": 2, "seq": 5, "msg": {}})
        await client._handle_incoming_message(msg)
        assert client._sid_map[2].seq == 5

    @pytest.mark.asyncio
    async def test_event_lifecycle_on_market_lifecycle_channel(self) -> None:
        """event_lifecycle should be accepted on market_lifecycle_v2 (no mismatch warning)."""
        client = self._make_client()
        self._setup_channel(client, "market_lifecycle_v2", sid=3)
        msg = orjson.dumps({
            "type": "event_lifecycle",
            "sid": 3,
            "seq": 1,
            "msg": {"event_ticker": "EVT-1"},
        })
        await client._handle_incoming_message(msg)
        # Should update seq without warning (None expected_channel skips validation)
        assert client._sid_map[3].seq == 1

    @pytest.mark.asyncio
    async def test_event_lifecycle_on_multivariate_channel(self) -> None:
        """event_lifecycle should also be accepted on multivariate_market_lifecycle."""
        client = self._make_client()
        self._setup_channel(client, "multivariate_market_lifecycle", sid=4)
        msg = orjson.dumps({
            "type": "event_lifecycle",
            "sid": 4,
            "seq": 1,
            "msg": {"event_ticker": "MVE-1"},
        })
        await client._handle_incoming_message(msg)
        assert client._sid_map[4].seq == 1

    @pytest.mark.asyncio
    async def test_user_order_routed_correctly(self) -> None:
        client = self._make_client()
        self._setup_channel(client, "user_orders", sid=5)
        msg = orjson.dumps({
            "type": "user_order",
            "sid": 5,
            "seq": 1,
            "msg": {"order_id": "o1", "status": "resting"},
        })
        await client._handle_incoming_message(msg)
        assert client._sid_map[5].seq == 1

    @pytest.mark.asyncio
    async def test_order_group_updates_routed_correctly(self) -> None:
        client = self._make_client()
        self._setup_channel(client, "order_group_updates", sid=6)
        msg = orjson.dumps({
            "type": "order_group_updates",
            "sid": 6,
            "seq": 1,
            "msg": {"event_type": "created", "order_group_id": "og1"},
        })
        await client._handle_incoming_message(msg)
        assert client._sid_map[6].seq == 1

    @pytest.mark.asyncio
    async def test_multivariate_market_lifecycle_routed(self) -> None:
        client = self._make_client()
        self._setup_channel(client, "multivariate_market_lifecycle", sid=7)
        msg = orjson.dumps({
            "type": "multivariate_market_lifecycle",
            "sid": 7,
            "seq": 1,
            "msg": {"market_ticker": "KXMVE-1", "event_type": "created"},
        })
        await client._handle_incoming_message(msg)
        assert client._sid_map[7].seq == 1

    @pytest.mark.asyncio
    async def test_subscribed_response_maps_sid(self) -> None:
        client = self._make_client()
        client.channels["ticker"] = ChannelState(name="ticker")
        client._pending_init_subs[1] = "ticker"
        msg = orjson.dumps({
            "type": "subscribed",
            "id": 1,
            "msg": {"channel": "ticker", "sid": 10},
        })
        await client._handle_incoming_message(msg)
        assert client.channels["ticker"].sid == 10
        assert 10 in client._sid_map

    @pytest.mark.asyncio
    async def test_callback_invoked(self) -> None:
        received: list[str] = []

        async def callback(msg: str) -> None:
            received.append(msg)

        client = self._make_client()
        client.on_message_callback = callback
        raw = orjson.dumps({"type": "trade", "sid": 1, "msg": {}})
        await client._handle_incoming_message(raw)
        # Give the create_task a chance to run
        import asyncio
        await asyncio.sleep(0.01)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_unknown_message_type_still_calls_callback(self) -> None:
        received: list[str] = []

        async def callback(msg: str) -> None:
            received.append(msg)

        client = self._make_client()
        client.on_message_callback = callback
        raw = orjson.dumps({"type": "some_future_type", "sid": 1, "msg": {}})
        await client._handle_incoming_message(raw)
        await asyncio.sleep(0.01)
        assert len(received) == 1


# =============================================================================
# Gap 2: Sequence gap propagation + resubscribe_channel
# =============================================================================


class TestSequenceGapPropagation:
    """Verify that sequence gaps raise KalshiSequenceGapError to the caller."""

    def _make_client(self) -> KalshiWebSocketClient:
        creds = mock_credentials()
        cfg = _test_config()
        return KalshiWebSocketClient(creds, cfg)

    def _setup_channel(self, client: KalshiWebSocketClient, channel: str, sid: int, seq: int = 0) -> None:
        state = ChannelState(name=channel)
        state.sid = sid
        state.seq = seq
        client.channels[channel] = state
        client._sid_map[sid] = state

    @pytest.mark.asyncio
    async def test_data_message_gap_raises(self) -> None:
        """A sequence gap in a data message should raise KalshiSequenceGapError."""
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=1, seq=5)
        msg = orjson.dumps({"type": "ticker", "sid": 1, "seq": 8, "msg": {}})
        with pytest.raises(KalshiSequenceGapError) as exc:
            await client._handle_incoming_message(msg)
        assert exc.value.channel == "ticker"
        assert exc.value.expected == 6
        assert exc.value.got == 8

    @pytest.mark.asyncio
    async def test_ok_message_gap_raises(self) -> None:
        """A sequence gap in an 'ok' response should raise KalshiSequenceGapError."""
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=1, seq=3)
        msg = orjson.dumps({"type": "ok", "sid": 1, "seq": 10})
        with pytest.raises(KalshiSequenceGapError) as exc:
            await client._handle_incoming_message(msg)
        assert exc.value.expected == 4
        assert exc.value.got == 10

    @pytest.mark.asyncio
    async def test_consecutive_seq_no_error(self) -> None:
        """No error when sequence increments by exactly 1."""
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=1, seq=5)
        msg = orjson.dumps({"type": "ticker", "sid": 1, "seq": 6, "msg": {}})
        await client._handle_incoming_message(msg)  # should not raise
        assert client._sid_map[1].seq == 6

    @pytest.mark.asyncio
    async def test_first_message_no_gap_check(self) -> None:
        """When seq is 0 (no messages yet), any seq is accepted."""
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=1, seq=0)
        msg = orjson.dumps({"type": "ticker", "sid": 1, "seq": 42, "msg": {}})
        await client._handle_incoming_message(msg)  # should not raise
        assert client._sid_map[1].seq == 42


class TestResubscribeChannel:
    """Verify the resubscribe_channel recovery method."""

    def _make_client(self) -> KalshiWebSocketClient:
        creds = mock_credentials()
        cfg = _test_config()
        return KalshiWebSocketClient(creds, cfg)

    def _setup_channel(self, client: KalshiWebSocketClient, channel: str, sid: int) -> None:
        state = ChannelState(name=channel, markets={"TICKER-1", "TICKER-2"})
        state.sid = sid
        state.seq = 10
        client.channels[channel] = state
        client._sid_map[sid] = state

    @pytest.mark.asyncio
    async def test_resubscribe_resets_state(self) -> None:
        """resubscribe_channel should reset sid and seq."""
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=5)
        # Simulate ws being None (no actual connection in unit test)
        client.ws = None
        await client.resubscribe_channel("ticker")
        state = client.channels["ticker"]
        assert state.sid is None
        assert state.seq == 0
        # Markets should be preserved for re-subscription
        assert state.markets == {"TICKER-1", "TICKER-2"}

    @pytest.mark.asyncio
    async def test_resubscribe_removes_from_sid_map(self) -> None:
        client = self._make_client()
        self._setup_channel(client, "ticker", sid=5)
        client.ws = None
        await client.resubscribe_channel("ticker")
        assert 5 not in client._sid_map

    @pytest.mark.asyncio
    async def test_resubscribe_unknown_channel_is_noop(self) -> None:
        client = self._make_client()
        client.ws = None
        await client.resubscribe_channel("nonexistent")  # should not raise


# =============================================================================
# Gap 4: Callback exception handling
# =============================================================================


class TestCallbackExceptionHandling:
    """Verify that exceptions in on_message_callback are logged, not propagated."""

    def _make_client(self) -> KalshiWebSocketClient:
        creds = mock_credentials()
        cfg = _test_config()
        return KalshiWebSocketClient(creds, cfg)

    @pytest.mark.asyncio
    async def test_callback_exception_does_not_propagate(self) -> None:
        """If callback raises, _handle_incoming_message should still complete."""
        async def bad_callback(msg: str) -> None:
            raise RuntimeError("callback boom")

        client = self._make_client()
        client.on_message_callback = bad_callback
        raw = orjson.dumps({"type": "some_type", "sid": 1, "msg": {}})
        # Should not raise
        await client._handle_incoming_message(raw)
        # Give the create_task a chance to run and fire done_callback
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio
    async def test_callback_exception_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        """The callback exception should be logged via _log_callback_exception."""
        async def bad_callback(msg: str) -> None:
            raise ValueError("test error in callback")

        client = self._make_client()
        client.on_message_callback = bad_callback
        raw = orjson.dumps({"type": "some_type", "sid": 1, "msg": {}})
        await client._handle_incoming_message(raw)
        await asyncio.sleep(0.05)
        assert any("callback failed" in r.message.lower() or "test error" in r.message.lower()
                    for r in caplog.records)
