![Unit Tests](https://github.com/Kalarb/pykalshi/actions/workflows/test.yml/badge.svg)
![Integration Tests](https://github.com/Kalarb/pykalshi/actions/workflows/integration.yml/badge.svg)

# pykalshi

Shared async Python client for the [Kalshi](https://kalshi.com) prediction market API.

Pure 1:1 reflection of the Kalshi API. Each method maps to exactly one API endpoint. Pagination loops, delta polling, and other application-level helpers belong in the consumer, not here.

## Install

```bash
pip install git+ssh://git@github.com/Kalarb/pykalshi.git

# With OpenTelemetry support
pip install "pykalshi[otel] @ git+ssh://git@github.com/Kalarb/pykalshi.git"
```

## Quick Start

### HTTP Client

```python
from pykalshi import KalshiCredentials, KalshiHttpClient, ClientConfig, Environment

creds = KalshiCredentials.from_key_file("your-key-id", "~/.kalshi/private.pem")
# Or from PEM string directly:
# creds = KalshiCredentials.from_pem_string("your-key-id", pem_string)

config = ClientConfig(environment=Environment.DEMO)

async with KalshiHttpClient(creds, config) as client:
    # Markets
    markets = await client.get_markets(status="open", limit=10)

    # Place an order
    order = await client.create_order(
        ticker="KXBTC-100K",
        side="yes",
        action="buy",
        count=10,
        yes_price=50,
    )

    # Cancel it
    await client.cancel_order(order["order"]["order_id"])
```

### WebSocket Client

```python
from pykalshi import KalshiCredentials, KalshiWebSocketClient, ClientConfig

creds = KalshiCredentials.from_key_file("your-key-id", "~/.kalshi/private.pem")

async def on_message(msg: str):
    print(msg)

ws = KalshiWebSocketClient(creds, ClientConfig(), on_message_callback=on_message)
await ws.connect()
await ws.add_market("KXBTC-100K", ["orderbook_delta", "ticker", "trade"])
await ws.listener_loop()
```

### Backward-Compatible Constructors

Drop-in replacements for the old `KalshiHttpClient(key_id, path, env)` pattern:

```python
from pykalshi import create_http_client, create_ws_client, Environment

client = create_http_client("key-id", "/path/to/key.pem", Environment.DEMO)
ws = create_ws_client("key-id", "/path/to/key.pem", Environment.DEMO)
```

## Configuration

| Env var | Default | Description |
|---|---|---|
| `KALSHI_HTTP_BASE_URL` | Derived from environment | Override HTTP base URL |
| `KALSHI_WS_BASE_URL` | Derived from environment | Override WS base URL |

`ClientConfig` fields: `environment`, `read_rate` (20.0), `write_rate` (10.0), `max_retries` (4), `base_retry_delay` (0.1s), timeout settings.

## API Coverage

| Category | Endpoints | Methods |
|---|:---:|---|
| Exchange | 4 | status, schedule, announcements, user_data_timestamp |
| Account | 2 | limits, endpoint_costs |
| Orders | 12 | CRUD, batch create/cancel, amend, decrease, queue positions |
| Order Groups | 7 | CRUD, reset, trigger, update limit |
| Portfolio | 4 | balance, positions, settlements, fills |
| Markets | 6 | get, list, orderbook, orderbooks (batch), trades, candlesticks |
| Events | 6 | get, list, multivariate, metadata, candlesticks, forecast |
| Series | 3 | get, list, fee_changes |
| Search | 2 | tags_by_categories, filters_by_sport |
| Historical | 7 | cutoff, markets, market, candlesticks, fills, orders, trades |
| API Keys | 4 | list, create, generate, delete |
| Communications | 10 | id, RFQ CRUD, Quote CRUD + accept |
| Live Data | 4 | milestone, legacy, batch, game_stats |
| Milestones | 2 | get, list |
| Structured Targets | 2 | get, list |
| Incentive Programs | 1 | list |
| **WebSocket** | 11 channels, 17 message types | Full coverage validated against AsyncAPI spec |

**Skipped** (not accessible): subaccounts, FCM, summary/resting_order_value.

## Test Matrix

Every endpoint has a unit test (mock transport). Integration tests hit the real Kalshi DEMO API.

### Exchange / Account / Search

| Method | Unit | Integration |
|---|:---:|:---:|
| `get_exchange_status` | Y | Y |
| `get_exchange_schedule` | Y | Y |
| `get_exchange_announcements` | Y | Y |
| `get_user_data_timestamp` | Y | Y |
| `get_api_limits` | Y | Y |
| `get_endpoint_costs` | Y | Y (skips if 403) |
| `get_tags_by_categories` | Y | Y |
| `get_filters_by_sport` | Y | Y |

### Orders

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_orders` | Y | Y | |
| `get_order` | Y | Y | via create+cancel lifecycle |
| `create_order` | Y | Y | places at 1c, won't fill |
| `cancel_order` | Y | Y | cleans up created order |
| `amend_order` | Y | Y | create → amend price → cancel |
| `decrease_order` | Y | Y | create count=2 → decrease to 1 → cancel |
| `batch_create_orders` | Y | Y | batch create 3 → batch cancel all |
| `batch_cancel_orders` | Y | Y | same test as batch_create |
| `get_queue_positions` | Y | Y | |
| `get_order_queue_position` | Y | Y | create → wait → get position → cancel |

### Order Groups

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_order_groups` | Y | Y | via lifecycle test |
| `create_order_group` | Y | Y | creates with limit=100 |
| `get_order_group` | Y | Y | with retry for propagation delay |
| `delete_order_group` | Y | Y | cleans up in finally block |
| `reset_order_group` | Y | Y | |
| `trigger_order_group` | Y | | would affect live groups |
| `update_order_group_limit` | Y | | would affect live groups |

### Portfolio

| Method | Unit | Integration |
|---|:---:|:---:|
| `get_balance` | Y | Y |
| `get_positions` | Y | Y |
| `get_settlements` | Y | Y |
| `get_fills` | Y | Y |

### Markets

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_market` | Y | Y | |
| `get_markets` | Y | Y | |
| `get_market_orderbook` | Y | Y | |
| `get_market_orderbooks` | Y | Y | batch, 3 tickers |
| `get_trades` | Y | Y | |
| `get_market_candlesticks` | Y | | needs series_ticker + time range |

### Events

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_event` | Y | Y | |
| `get_events` | Y | Y | |
| `get_multivariate_events` | Y | Y | |
| `get_event_metadata` | Y | Y | |
| `get_event_candlesticks` | Y | | needs series_ticker + time range |
| `get_forecast_percentile_history` | Y | | needs series_ticker + time range |

### Series

| Method | Unit | Integration |
|---|:---:|:---:|
| `get_series` | Y | Y |
| `get_series_list` | Y | Y |
| `get_fee_changes` | Y | Y |

### Historical

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_historical_cutoff` | Y | Y | |
| `get_historical_markets` | Y | Y | |
| `get_historical_market` | Y | | needs specific archived ticker |
| `get_historical_market_candlesticks` | Y | | needs archived ticker + time range |
| `get_historical_fills` | Y | Y | |
| `get_historical_orders` | Y | Y | |
| `get_historical_trades` | Y | Y | |

### API Keys

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_api_keys` | Y | Y | |
| `create_api_key` | Y | Y (skips if 400) | throwaway RSA pubkey |
| `generate_api_key` | Y | | |
| `delete_api_key` | Y | Y | cleans up created key |

### Communications

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_communications_id` | Y | Y | |
| `get_rfqs` | Y | Y | |
| `create_rfq` | Y | Y (skips if error) | |
| `get_rfq` | Y | Y | via create+delete lifecycle |
| `delete_rfq` | Y | Y | cleans up created RFQ |
| `get_quotes` | Y | Y (skips if 400) | |
| `create_quote` | Y | | needs counterparty RFQ |
| `get_quote` | Y | | |
| `delete_quote` | Y | | |
| `accept_quote` | Y | | needs counterparty RFQ |

### Live Data / Milestones / Structured Targets / Incentive Programs

| Method | Unit | Integration | Notes |
|---|:---:|:---:|---|
| `get_live_data` | Y | | needs active milestone ID |
| `get_live_data_legacy` | | | deprecated endpoint |
| `get_live_data_batch` | Y | | needs active milestone IDs |
| `get_game_stats` | Y | | needs active milestone ID |
| `get_milestone` | Y | | needs specific milestone ID |
| `get_milestones` | Y | Y | |
| `get_structured_target` | Y | | needs specific target ID |
| `get_structured_targets` | Y | Y | |
| `get_incentive_programs` | Y | Y | |

### WebSocket — Unit Tests

| Check | Status |
|---|:---:|
| All 17 message types in `MSG_TYPE_TO_CHANNEL` | Y |
| All 11 channels referenced | Y |
| `event_lifecycle` multi-channel handling | Y |
| Message routing + sequence tracking (7 channel types) | Y |
| Subscription handshake (SID mapping) | Y |
| Callback invocation | Y |
| Unknown message type passthrough | Y |
| Validated against live AsyncAPI spec | Y |

### WebSocket — Integration Tests (PROD)

| Test | Channel/Operation | Verified |
|---|---|---|
| `test_ws_connect_and_receive_orderbook` | `orderbook_delta` subscribe + snapshot | Data received |
| `test_ws_receive_ticker` | `ticker` subscribe + message | Data received |
| `test_ws_receive_trade` | `trade` subscribe + message | Data received |
| `test_ws_subscribe_fill` | `fill` subscribe | SID received |
| `test_ws_subscribe_market_positions` | `market_positions` subscribe | SID received |
| `test_ws_subscribe_market_lifecycle` | `market_lifecycle_v2` subscribe + wait | Data received (may be flaky) |
| `test_ws_subscribe_user_orders` | `user_orders` subscribe | SID received |
| `test_ws_subscribe_communications` | `communications` subscribe | SID received |
| `test_ws_add_market` | `add_market` (KXBTC15M + KXBTCD) | Snapshot for added market |
| `test_ws_remove_market` | `remove_market` | No data for removed market |
| `test_ws_unsubscribe_all` | `unsubscribe_all` | No data after unsub |
| `test_ws_multi_channel_subscribe` | Multi-channel (orderbook + ticker) | Both types received |
| `test_ws_request_snapshot` | `request_snapshot` (get_snapshot) | Second snapshot received |

## Architecture

```
pykalshi/
  auth.py            KalshiCredentials (RSA-PSS signing)
  config.py          Environment + ClientConfig (frozen dataclass)
  http_client.py     KalshiHttpClient (rate limiting, retry, OTel)
  ws_client.py       KalshiWebSocketClient (subscriptions, reconnect)
  rate_limiter.py    ReadWriteTokenBucket (disjoint read/write)
  protocols.py       Typed Protocol classes (consumer contract)
  exceptions.py      KalshiError hierarchy
  _observability.py  OTel no-op facade (zero overhead when not installed)
  api/               One module per domain (orders, markets, events, ...)
  models/            Pydantic v2 models (enums, common types)
  testing/           Mock transport factory + pytest fixtures
```

## Testing

```bash
# Unit tests (fast, no credentials needed)
uv run pytest tests/ -v -m "not integration"

# Integration tests (requires .env with DEMO credentials)
uv run pytest tests/test_integration.py -v

# Spec validation (fetches live OpenAPI + AsyncAPI from docs.kalshi.com)
uv run pytest tests/test_spec_validation.py -v

# Everything
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```

## Typed Contract

Consumers should type-annotate against Protocol classes, not concrete implementations:

```python
from pykalshi import KalshiHttpClientProtocol

async def fetch_balance(client: KalshiHttpClientProtocol) -> float:
    result = await client.get_balance()
    return result["balance"]
```

This enables mocking and swapping implementations freely. The library includes a `py.typed` marker (PEP 561) for full type checking support.
