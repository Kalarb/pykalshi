"""Async WebSocket client for the Kalshi API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, Optional

import orjson
import websockets

from .auth import KalshiCredentials
from .config import ClientConfig
from .exceptions import KalshiSequenceGapError
from ._observability import get_meter, get_tracer

logger = logging.getLogger(__name__)

# Maps message type -> expected channel name.
# None means the message can arrive on multiple channels (skip validation).
MSG_TYPE_TO_CHANNEL: Dict[str, str | None] = {
    # Orderbook
    "orderbook_snapshot": "orderbook_delta",
    "orderbook_delta": "orderbook_delta",
    # Market Data
    "ticker": "ticker",
    "trade": "trade",
    # User Data
    "fill": "fill",
    "market_position": "market_positions",
    "user_order": "user_orders",
    # Lifecycle
    "market_lifecycle_v2": "market_lifecycle_v2",
    "event_lifecycle": None,  # arrives on market_lifecycle_v2 OR multivariate_market_lifecycle
    "multivariate_market_lifecycle": "multivariate_market_lifecycle",
    "multivariate_lookup": "multivariate",
    # Communications (RFQs, Quotes)
    "rfq_created": "communications",
    "rfq_deleted": "communications",
    "quote_created": "communications",
    "quote_accepted": "communications",
    "quote_executed": "communications",
    # Order Groups
    "order_group_updates": "order_group_updates",
}


@dataclass
class ChannelState:
    """Tracks the state of a specific channel."""

    name: str
    markets: set[str] = field(default_factory=set)
    pending_markets: set[str] = field(default_factory=set)
    sid: Optional[int] = None
    seq: int = 0


def _log_callback_exception(task: asyncio.Task[None]) -> None:
    if not task.cancelled() and task.exception():
        logger.error("Message callback failed: %s", task.exception())


class KalshiWebSocketClient:
    """Robust WebSocket client with auto-reconnect and subscription management."""

    def __init__(
        self,
        credentials: KalshiCredentials,
        config: ClientConfig = ClientConfig(),
        *,
        on_message_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> None:
        self._credentials = credentials
        self._config = config
        self.ws: websockets.WebSocketClientProtocol | None = None
        self._url_suffix = "/trade-api/ws/v2"
        self._message_id = 1
        self._listening = False
        self.on_message_callback = on_message_callback
        self.channels: dict[str, ChannelState] = {}
        self._sid_map: dict[int, ChannelState] = {}
        self._pending_init_subs: dict[int, str] = {}

        tracer = get_tracer("pykalshi.ws")
        meter = get_meter("pykalshi.ws")
        self._tracer = tracer
        self._reconnects = meter.create_counter(
            "pykalshi.ws.reconnects_total",
            description="Total WebSocket reconnection attempts",
        )
        self._sequence_gaps = meter.create_counter(
            "pykalshi.ws.sequence_gaps_total",
            description="Total sequence gap events detected",
        )
        self._messages_received = meter.create_counter(
            "pykalshi.ws.messages_received_total",
            description="Total WebSocket messages received",
        )

    async def connect(self) -> None:
        """Establish the WebSocket connection."""
        host = self._config.resolved_ws_url + self._url_suffix
        auth_headers = self._credentials.auth_headers("GET", self._url_suffix)
        logger.info("Connecting to %s...", host)
        self.ws = await websockets.connect(host, additional_headers=auth_headers)
        self._listening = True
        logger.info("WebSocket connected.")

    async def close(self) -> None:
        """Graceful shutdown."""
        self._listening = False
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket connection closed.")

    async def listener_loop(self) -> None:
        """Read messages forever with auto-reconnect."""
        retry_delay = 1
        while self._listening:
            try:
                async for message in self.ws:
                    retry_delay = 1
                    await self._handle_incoming_message(message)
                raise websockets.ConnectionClosed(1000, "Loop ended unexpectedly")
            except Exception as e:
                if not self._listening:
                    break
                logger.error("Socket error: %s", e)
                await self._handle_connection_loss()
                logger.info("Reconnecting in %d seconds...", retry_delay)
                await asyncio.sleep(retry_delay)
                with self._tracer.start_as_current_span("ws.reconnect") as span:
                    self._reconnects.add(1)
                    try:
                        await self.connect()
                        await self._recover_subscriptions()
                        retry_delay = 1
                        span.set_attribute("ws.reconnect.success", True)
                    except Exception as reconnect_err:
                        logger.error("Reconnection failed: %s", reconnect_err)
                        span.set_attribute("ws.reconnect.success", False)
                        retry_delay = min(retry_delay * 2, 32)

    async def _handle_incoming_message(self, message: str) -> None:
        """Parse message, update sequence state, trigger callback."""
        self._messages_received.add(1)
        try:
            data = orjson.loads(message)
        except orjson.JSONDecodeError as e:
            logger.error("JSON decode error: %s", e)
            return

        msg_type = data.get("type")
        resp_id = data.get("id")

        if msg_type == "subscribed":
            msg_body = data.get("msg", {})
            sid = msg_body.get("sid")
            channel_name = self._pending_init_subs.pop(resp_id, None)
            if channel_name and channel_name in self.channels:
                chan_state = self.channels[channel_name]
                chan_state.sid = sid
                self._sid_map[sid] = chan_state
                if chan_state.pending_markets:
                    await self._send_update_sub(
                        sid, list(chan_state.pending_markets), "add_markets"
                    )
                    chan_state.pending_markets.clear()

        elif msg_type == "ok":
            sid = data.get("sid")
            seq = data.get("seq")
            server_tickers = data.get("market_tickers")
            chan_state = self._sid_map.get(sid)
            if chan_state and server_tickers is not None:
                chan_state.markets = set(server_tickers)
            if chan_state and seq is not None:
                if chan_state.seq != 0 and (chan_state.seq + 1) != seq:
                    self._sequence_gaps.add(1)
                    logger.warning(
                        "Gap on %s: expected %d, got %d",
                        chan_state.name,
                        chan_state.seq + 1,
                        seq,
                    )
                    raise KalshiSequenceGapError(
                        chan_state.name, chan_state.seq + 1, seq
                    )
                chan_state.seq = seq

        elif msg_type == "unsubscribed":
            sid = data.get("sid")
            self._sid_map.pop(sid, None)

        elif msg_type in MSG_TYPE_TO_CHANNEL:
            sid = data.get("sid")
            seq = data.get("seq")
            chan_state = self._sid_map.get(sid)
            if chan_state:
                expected_channel = MSG_TYPE_TO_CHANNEL[msg_type]
                if expected_channel is not None and chan_state.name != expected_channel:
                    logger.warning(
                        "Mismatch! Received %s (needs %s) on channel %s (SID %s). Ignoring.",
                        msg_type,
                        expected_channel,
                        chan_state.name,
                        sid,
                    )
                elif seq is not None:
                    if chan_state.seq != 0 and (chan_state.seq + 1) != seq:
                        self._sequence_gaps.add(1)
                        logger.warning(
                            "Gap on %s: expected %d, got %d",
                            chan_state.name,
                            chan_state.seq + 1,
                            seq,
                        )
                        raise KalshiSequenceGapError(
                            chan_state.name, chan_state.seq + 1, seq
                        )
                    chan_state.seq = seq

        if self.on_message_callback:
            task = asyncio.create_task(self.on_message_callback(message))
            task.add_done_callback(_log_callback_exception)

    async def add_markets(self, market_tickers: list[str], channels: list[str]) -> None:
        """Batch-subscribe multiple markets across channels."""
        for channel_name in channels:
            if channel_name not in self.channels:
                self.channels[channel_name] = ChannelState(name=channel_name)
            chan_state = self.channels[channel_name]
            new_tickers = [t for t in market_tickers if t not in chan_state.markets]
            if not new_tickers:
                continue
            chan_state.markets.update(new_tickers)
            if chan_state.sid is not None:
                await self._send_update_sub(chan_state.sid, new_tickers, "add_markets")
            else:
                await self._send_subscribe(channel_name, list(chan_state.markets))

    async def add_market(self, market_ticker: str, channels: list[str]) -> None:
        """Add a single market to subscription list."""
        for channel_name in channels:
            if channel_name not in self.channels:
                self.channels[channel_name] = ChannelState(name=channel_name)
            chan_state = self.channels[channel_name]
            if market_ticker in chan_state.markets:
                continue
            chan_state.markets.add(market_ticker)
            if chan_state.sid is None:
                is_pending = any(
                    c == channel_name for c in self._pending_init_subs.values()
                )
                if not is_pending:
                    await self._send_subscribe(channel_name, [market_ticker])
                else:
                    chan_state.pending_markets.add(market_ticker)
            else:
                await self._send_update_sub(
                    chan_state.sid, [market_ticker], "add_markets"
                )

    async def remove_market(self, market_ticker: str, channels: list[str]) -> None:
        """Remove a market from subscription list."""
        for channel_name in channels:
            if channel_name not in self.channels:
                continue
            chan_state = self.channels[channel_name]
            if market_ticker not in chan_state.markets:
                continue
            chan_state.markets.remove(market_ticker)
            if chan_state.sid is not None:
                if len(chan_state.markets) == 0:
                    await self._send_unsubscribe(chan_state.sid)
                    self._sid_map.pop(chan_state.sid, None)
                    chan_state.sid = None
                    chan_state.seq = 0
                    del self.channels[channel_name]
                else:
                    await self._send_update_sub(
                        sid=chan_state.sid,
                        tickers=[market_ticker],
                        action="delete_markets",
                    )

    async def unsubscribe_all(self) -> None:
        """Unsubscribe from all channels and markets."""
        to_remove = [
            (channel_name, list(state.markets))
            for channel_name, state in self.channels.items()
            if state.markets
        ]
        for channel_name, tickers in to_remove:
            for ticker in tickers:
                await self.remove_market(ticker, [channel_name])
        logger.info("Unsubscribed from all channels.")

    async def request_snapshot(
        self, market_tickers: list[str], channel: str = "orderbook_delta"
    ) -> None:
        """Request orderbook snapshot without modifying subscription."""
        chan_state = self.channels.get(channel)
        if chan_state is None or chan_state.sid is None:
            raise ValueError(f"Not subscribed to {channel}")
        await self._send_update_sub(chan_state.sid, market_tickers, "get_snapshot")

    # --- Internal helpers ---

    async def _handle_connection_loss(self) -> None:
        self._sid_map.clear()
        self._pending_init_subs.clear()
        for state in self.channels.values():
            state.sid = None
            state.seq = 0

    async def _recover_subscriptions(self) -> None:
        if not self.channels:
            return
        logger.info("Recovering %d channels...", len(self.channels))
        for name, state in self.channels.items():
            if state.markets:
                await self._send_subscribe(name, list(state.markets))

    async def _send_subscribe(self, channel_name: str, tickers: list[str]) -> None:
        msg = {
            "id": self._message_id,
            "cmd": "subscribe",
            "params": {"channels": [channel_name], "market_tickers": tickers},
        }
        self._pending_init_subs[self._message_id] = channel_name
        self._message_id += 1
        if self.ws:
            await self.ws.send(orjson.dumps(msg))

    async def _send_unsubscribe(self, sid: int) -> None:
        msg = {
            "id": self._message_id,
            "cmd": "unsubscribe",
            "params": {"sids": [sid]},
        }
        self._message_id += 1
        if self.ws:
            await self.ws.send(orjson.dumps(msg))

    async def _send_update_sub(
        self, sid: int, tickers: list[str], action: str
    ) -> None:
        msg = {
            "id": self._message_id,
            "cmd": "update_subscription",
            "params": {"sids": [sid], "market_tickers": tickers, "action": action},
        }
        self._message_id += 1
        if self.ws:
            await self.ws.send(orjson.dumps(msg))
