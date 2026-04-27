![REST Unit Tests](https://github.com/Kalarb/pykalshi/actions/workflows/rest-unit-tests.yml/badge.svg)
![REST Integration](https://github.com/Kalarb/pykalshi/actions/workflows/rest-integration.yml/badge.svg)
![OpenAPI Validation](https://github.com/Kalarb/pykalshi/actions/workflows/openapi-validation.yml/badge.svg)

![WS Unit Tests](https://github.com/Kalarb/pykalshi/actions/workflows/ws-unit-tests.yml/badge.svg)
![WS Integration](https://github.com/Kalarb/pykalshi/actions/workflows/ws-integration.yml/badge.svg)
![AsyncAPI Validation](https://github.com/Kalarb/pykalshi/actions/workflows/asyncapi-validation.yml/badge.svg)

![Lint](https://github.com/Kalarb/pykalshi/actions/workflows/lint.yml/badge.svg)

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

#### Backward-Compatible Constructors

Drop-in replacements for the old `KalshiHttpClient(key_id, path, env)` pattern:

```python
from pykalshi import create_http_client, create_ws_client, Environment

client = create_http_client("key-id", "/path/to/key.pem", Environment.DEMO)
ws = create_ws_client("key-id", "/path/to/key.pem", Environment.DEMO)
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

## Typed Models

All API response and request types are available as Pydantic v2 models, auto-generated from the Kalshi OpenAPI spec. This gives you IDE autocomplete, field descriptions, and runtime validation.

```python
from pykalshi.models import CreateOrderResponse, GetMarketsResponse, Order

# Parse raw API response into a typed model
raw = await client.create_order(ticker="KXBTC-100K", side="yes", action="buy", count=1, yes_price=50)
resp = CreateOrderResponse(**raw)
print(resp.order.order_id)
print(resp.order.status)          # IDE autocomplete works here
print(resp.order.yes_price_dollars)

# List endpoints return typed collections
raw_markets = await client.get_markets(status="open", limit=5)
markets = GetMarketsResponse(**raw_markets)
for market in markets.markets:
    print(f"{market.ticker}: {market.yes_bid_dollars}/{market.yes_ask_dollars}")
```

**144 types** generated across 4 files:

| File | Contents | Count |
|------|----------|:-----:|
| `models/enums.py` | `OrderStatus`, `ExchangeInstance`, `SelfTradePreventionType` | 3 |
| `models/core.py` | `Order`, `Market`, `Fill`, `Position`, `ExchangeStatus`, ... | 49 |
| `models/requests.py` | `CreateOrderRequest`, `AmendOrderRequest`, ... | 16 |
| `models/responses.py` | `CreateOrderResponse`, `GetOrdersResponse`, `GetMarketsResponse`, ... | 76 |

All models use `extra="ignore"` (forward-compatible with spec additions) and include field descriptions from the spec for IDE tooltips.

## Configuration

### HTTP

| Field | Default | Description |
|---|---|---|
| `KALSHI_HTTP_BASE_URL` (env var) | Derived from environment | Override HTTP base URL |
| `environment` | `DEMO` | `Environment.DEMO` or `Environment.PROD` |
| `read_rate` | 20.0 | Read requests per second |
| `write_rate` | 10.0 | Write requests per second |
| `max_retries` | 4 | Retry count for 429s and network errors |
| `base_retry_delay` | 0.1s | Initial backoff delay |
| `connect_timeout` | 5.0s | Connection timeout |
| `read_timeout` | 30.0s | Read timeout |
| `write_timeout` | 10.0s | Write timeout |

### WebSocket

| Field | Default | Description |
|---|---|---|
| `KALSHI_WS_BASE_URL` (env var) | Derived from environment | Override WS base URL |

WebSocket reconnection uses exponential backoff with sequence gap detection.

## API Coverage & Tests

Every implemented endpoint has a unit test (mock transport). Integration tests hit the real Kalshi DEMO API (HTTP) or PROD API (WebSocket, read-only).

**Skipped** (not accessible): subaccounts, FCM, summary/resting_order_value.

### HTTP

#### Exchange

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_exchange_status` | Y | Y | Y | |
| `get_exchange_schedule` | Y | Y | Y | |
| `get_exchange_announcements` | Y | Y | Y | |
| `get_user_data_timestamp` | Y | Y | Y | |

#### Account

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_api_limits` | Y | Y | Y | |
| `get_endpoint_costs` | Y | Y | Y | skips if 403 |

#### Orders

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_orders` | Y | Y | Y | |
| `get_order` | Y | Y | Y | via create+cancel lifecycle |
| `create_order` | Y | Y | Y | places at 1c, won't fill |
| `cancel_order` | Y | Y | Y | cleans up created order |
| `amend_order` | Y | Y | Y | create -> amend price -> cancel |
| `decrease_order` | Y | Y | Y | create count=2 -> decrease to 1 -> cancel |
| `batch_create_orders` | Y | Y | Y | batch create 3 -> batch cancel all |
| `batch_cancel_orders` | Y | Y | Y | same test as batch_create |
| `get_queue_positions` | Y | Y | Y | |
| `get_order_queue_position` | Y | Y | Y | create -> wait -> get position -> cancel |

#### Order Groups

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_order_groups` | Y | Y | Y | via lifecycle test |
| `create_order_group` | Y | Y | Y | creates with limit=100 |
| `get_order_group` | Y | Y | Y | with retry for propagation delay |
| `delete_order_group` | Y | Y | Y | cleans up in finally block |
| `reset_order_group` | Y | Y | Y | |
| `update_order_group_limit` | Y | Y | Y | update limit in lifecycle test |
| `trigger_order_group` | Y | Y | | would affect live groups |

#### Portfolio

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_balance` | Y | Y | Y | |
| `get_positions` | Y | Y | Y | |
| `get_settlements` | Y | Y | Y | |
| `get_fills` | Y | Y | Y | |

#### Markets

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_market` | Y | Y | Y | |
| `get_markets` | Y | Y | Y | |
| `get_market_orderbook` | Y | Y | Y | |
| `get_market_orderbooks` | Y | Y | Y | batch, 3 tickers |
| `get_trades` | Y | Y | Y | |
| `get_market_candlesticks` | Y | Y | Y | via series + market ticker |

#### Events

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_event` | Y | Y | Y | |
| `get_events` | Y | Y | Y | |
| `get_multivariate_events` | Y | Y | Y | |
| `get_event_metadata` | Y | Y | Y | |
| `get_event_candlesticks` | Y | Y | Y | via series + event ticker |
| `get_forecast_percentile_history` | Y | Y | Y | skips if unsupported on DEMO |

#### Series

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_series` | Y | Y | Y | |
| `get_series_list` | Y | Y | Y | |
| `get_fee_changes` | Y | Y | Y | |

#### Search

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_tags_by_categories` | Y | Y | Y | |
| `get_filters_by_sport` | Y | Y | Y | |

#### Historical

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_historical_cutoff` | Y | Y | Y | |
| `get_historical_markets` | Y | Y | Y | |
| `get_historical_market` | Y | Y | Y | uses ticker from history list |
| `get_historical_market_candlesticks` | Y | Y | Y | skips if no historical data |
| `get_historical_fills` | Y | Y | Y | |
| `get_historical_orders` | Y | Y | Y | |
| `get_historical_trades` | Y | Y | Y | |

#### API Keys

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_api_keys` | Y | Y | Y | |
| `create_api_key` | Y | Y | Y | skips if 400; throwaway RSA pubkey |
| `generate_api_key` | Y | Y | Y | skips if 403; cleans up after |
| `delete_api_key` | Y | Y | Y | cleans up created key |

#### Communications

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_communications_id` | Y | Y | Y | |
| `get_rfqs` | Y | Y | Y | |
| `create_rfq` | Y | Y | Y | skips if error |
| `get_rfq` | Y | Y | Y | via create+delete lifecycle |
| `delete_rfq` | Y | Y | Y | cleans up created RFQ |
| `get_quotes` | Y | Y | Y | skips if 400 |
| `create_quote` | Y | Y | | needs counterparty RFQ |
| `get_quote` | Y | Y | | needs counterparty RFQ |
| `delete_quote` | Y | Y | | needs counterparty RFQ |
| `accept_quote` | Y | Y | | needs two accounts |

#### Live Data

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_live_data` | Y | Y | Y | skips if 404/400 |
| `get_live_data_legacy` | Y | | | deprecated endpoint |
| `get_live_data_batch` | Y | Y | Y | skips if 404/400 |
| `get_game_stats` | Y | Y | Y | skips if 404/400 |

#### Milestones

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_milestones` | Y | Y | Y | |
| `get_milestone` | Y | Y | Y | uses ID from list |

#### Structured Targets

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_structured_targets` | Y | Y | Y | |
| `get_structured_target` | Y | Y | Y | uses ID from list |

#### Incentive Programs

| Method | Impl | Unit | Integration | Notes |
|---|:---:|:---:|:---:|---|
| `get_incentive_programs` | Y | Y | Y | |

### WebSocket

#### Unit Tests

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

#### Integration Tests (PROD)

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
  Core:
    auth.py            KalshiCredentials (RSA-PSS signing)
    config.py          Environment + ClientConfig (frozen dataclass)
    protocols.py       Typed Protocol classes (consumer contract)
    exceptions.py      KalshiError hierarchy
    rate_limiter.py    ReadWriteTokenBucket (disjoint read/write)
    _observability.py  OTel no-op facade (zero overhead when not installed)

  HTTP:
    http_client.py     KalshiHttpClient (rate limiting, retry, OTel)
    api/               One module per domain (orders, markets, events, ...)

  WebSocket:
    ws_client.py       KalshiWebSocketClient (subscriptions, reconnect)

  Shared:
    models/            Pydantic v2 models — auto-generated from OpenAPI spec
      enums.py           Enum types (OrderStatus, ExchangeInstance, ...)
      core.py            Domain objects (Order, Market, Fill, Position, ...)
      requests.py        Request body schemas (CreateOrderRequest, ...)
      responses.py       Response wrappers (CreateOrderResponse, GetOrdersResponse, ...)
    testing/           Mock transport factory + pytest fixtures

tools/
  generate_models.py   Fetch OpenAPI spec and generate Pydantic models
  sync_docstrings.py   Sync API function docstrings from OpenAPI spec
```

## Tooling

The `tools/` directory contains scripts that sync parts of the codebase with the Kalshi OpenAPI spec:

```bash
# Regenerate Pydantic models (enums, core objects, requests, responses)
uv run python tools/generate_models.py

# Sync API function docstrings (summary + description from spec)
uv run python tools/sync_docstrings.py
```

Models are auto-generated because they tolerate spec inaccuracies (`extra="ignore"`). API function signatures are hand-written and manually verified against real API behavior.

## Testing

### HTTP

```bash
# Unit tests (fast, no credentials needed)
uv run pytest tests/test_http_client.py tests/test_auth.py tests/test_rate_limiter.py -v

# Integration tests (requires .env with DEMO credentials)
uv run pytest tests/test_integration.py -v

# OpenAPI spec validation (fetches live spec from docs.kalshi.com)
uv run pytest tests/test_openapi_validation.py -v -s
```

### WebSocket

```bash
# Unit tests (fast, no credentials needed)
uv run pytest tests/test_ws_client.py -v

# Integration tests (requires .env with PROD read-only credentials)
uv run pytest tests/test_ws_integration.py -v

# AsyncAPI spec validation (fetches live spec from docs.kalshi.com)
uv run pytest tests/test_asyncapi_validation.py -v -s
```

### All

```bash
# Everything
uv run pytest tests/ -v

# Lint
uv run ruff check src/ tests/
```

## Typed Contract

Consumers should type-annotate against Protocol classes, not concrete implementations:

### HTTP

```python
from pykalshi import KalshiHttpClientProtocol

async def fetch_balance(client: KalshiHttpClientProtocol) -> float:
    result = await client.get_balance()
    return result["balance"]
```

### WebSocket

```python
from pykalshi import KalshiWebSocketClientProtocol

async def subscribe_orderbook(ws: KalshiWebSocketClientProtocol, ticker: str) -> None:
    await ws.subscribe("orderbook_delta", [ticker])
```

This enables mocking and swapping implementations freely. The library includes a `py.typed` marker (PEP 561) for full type checking support.
