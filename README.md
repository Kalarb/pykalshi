[![PyPI](https://img.shields.io/pypi/v/pykalshi-client)](https://pypi.org/project/pykalshi-client/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
![REST Unit Tests](https://github.com/Kalarb/pykalshi/actions/workflows/rest-unit-tests.yml/badge.svg)
![REST Integration](https://github.com/Kalarb/pykalshi/actions/workflows/rest-integration.yml/badge.svg)
[![OpenAPI](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/yardboy27/65579a629076066fcbf09520ca76301a/raw/openapi-status.json)](https://github.com/Kalarb/pykalshi/actions/workflows/openapi-validation.yml)

![WS Unit Tests](https://github.com/Kalarb/pykalshi/actions/workflows/ws-unit-tests.yml/badge.svg)
![WS Integration](https://github.com/Kalarb/pykalshi/actions/workflows/ws-integration.yml/badge.svg)
[![AsyncAPI](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/yardboy27/65579a629076066fcbf09520ca76301a/raw/asyncapi-status.json)](https://github.com/Kalarb/pykalshi/actions/workflows/asyncapi-validation.yml)

![Lint](https://github.com/Kalarb/pykalshi/actions/workflows/lint.yml/badge.svg)

# pykalshi-client

Async Python client for the [Kalshi](https://kalshi.com) prediction market API.

Pure 1:1 reflection of the Kalshi API. Each method maps to exactly one API endpoint. Pagination loops, delta polling, and other application-level helpers belong in the consumer, not here.

## Install

```bash
pip install pykalshi-client

# With OpenTelemetry support
pip install "pykalshi-client[otel]"
```

> **Note:** The PyPI package is `pykalshi-client`, but the import name is `pykalshi`:
> ```python
> from pykalshi import KalshiHttpClient
> ```

## Quick Start

### HTTP Client

```python
from pykalshi import KalshiCredentials, KalshiHttpClient, ClientConfig, Environment

creds = KalshiCredentials.from_key_file("your-key-id", "~/.kalshi/private.pem")
# Or from PEM string directly:
# creds = KalshiCredentials.from_pem_string("your-key-id", pem_string)

config = ClientConfig(environment=Environment.DEMO)

async with KalshiHttpClient(creds, config) as client:
    # Markets — returns typed GetMarketsResponse
    resp = await client.get_markets(status="open", limit=10)
    for market in resp.markets:
        print(f"{market.ticker}: {market.yes_bid_dollars}/{market.yes_ask_dollars}")

    # Place an order — returns typed CreateOrderResponse
    result = await client.create_order(
        ticker="KXBTC-100K",
        side="yes",
        action="buy",
        count=10,
        yes_price=50,
    )
    print(result.order.order_id)

    # Cancel it
    await client.cancel_order(result.order.order_id)

    # Raw dict access is still available via .model_dump()
    raw = result.model_dump()
    print(raw["order"]["order_id"])
```

#### Convenience Constructors

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

# listener_loop auto-reconnects on network errors.
# Sequence gaps raise KalshiSequenceGapError — handle with resubscribe_channel:
from pykalshi.exceptions import KalshiSequenceGapError

while True:
    try:
        await ws.listener_loop()
    except KalshiSequenceGapError as e:
        await ws.resubscribe_channel(e.channel)
```

## Typed Models

All client methods return typed Pydantic v2 response models — no manual parsing needed. Models are auto-generated from the Kalshi OpenAPI and AsyncAPI specs, giving you IDE autocomplete, field descriptions, and runtime validation.

```python
# Responses are already typed — just use attribute access
result = await client.create_order(ticker="KXBTC-100K", side="yes", action="buy", count=1, yes_price=50)
print(result.order.order_id)
print(result.order.status)          # IDE autocomplete works here
print(result.order.yes_price_dollars)

markets = await client.get_markets(status="open", limit=5)
for market in markets.markets:
    print(f"{market.ticker}: {market.yes_bid_dollars}/{market.yes_ask_dollars}")

# Raw dict access via .model_dump() or the lower-level api.* modules
from pykalshi.api import markets as markets_api
raw = await markets_api.get_markets(client, status="open", limit=5)  # returns dict[str, Any]
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

WebSocket reconnection uses exponential backoff. Sequence gaps raise `KalshiSequenceGapError` for consumer-controlled recovery via `resubscribe_channel()`.

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

#### Channels

| Channel | Auth | Message Types | Impl | Unit | Integration | Notes |
|---|:---:|---|:---:|:---:|:---:|---|
| `orderbook_delta` | | `orderbook_snapshot`, `orderbook_delta` | Y | Y | Y | sequence tracking |
| `ticker` | | `ticker` | Y | Y | Y | price/volume/OI updates |
| `trade` | | `trade` | Y | Y | Y | public trade notifications |
| `fill` | Y | `fill` | Y | Y | Y | user fill notifications |
| `market_positions` | Y | `market_position` | Y | Y | Y | real-time position updates |
| `user_orders` | Y | `user_order` | Y | Y | Y | order state changes |
| `market_lifecycle_v2` | | `market_lifecycle_v2`, `event_lifecycle` | Y | Y | Y | may be flaky |
| `multivariate_market_lifecycle` | | `multivariate_market_lifecycle`, `event_lifecycle` | Y | Y | | |
| `multivariate` | | `multivariate_lookup` | Y | Y | | |
| `communications` | Y | `rfq_created`, `rfq_deleted`, `quote_created`, `quote_accepted`, `quote_executed` | Y | Y | Y | RFQ/quote notifications |
| `order_group_updates` | Y | `order_group_updates` | Y | Y | | |

#### Client Operations

| Method | Purpose | Impl | Unit | Integration | Notes |
|---|---|:---:|:---:|:---:|---|
| `connect()` | Establish WS connection + auth | Y | Y | Y | |
| `close()` | Gracefully close connection | Y | Y | Y | |
| `listener_loop()` | Read messages with auto-reconnect | Y | Y | Y | raises `KalshiSequenceGapError` on gaps |
| `add_market()` | Subscribe market to channels | Y | Y | Y | |
| `add_markets()` | Batch subscribe markets | Y | Y | Y | |
| `remove_market()` | Unsubscribe market from channels | Y | Y | Y | |
| `unsubscribe_all()` | Unsubscribe from everything | Y | Y | Y | |
| `request_snapshot()` | Request orderbook snapshot | Y | Y | Y | `get_snapshot` action |
| `resubscribe_channel()` | Recover from sequence gap | Y | Y | Y | called after `KalshiSequenceGapError` |

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
    models/            Pydantic v2 models — auto-generated from OpenAPI/AsyncAPI specs
      enums.py           Enum types (OrderStatus, ExchangeInstance, ...)
      core.py            Domain objects (Order, Market, Fill, Position, ...)
      requests.py        Request body schemas (CreateOrderRequest, ...)
      responses.py       Response wrappers (CreateOrderResponse, GetOrdersResponse, ...)
      ws.py              WebSocket message models (Channel enum, FillMsg, TickerMsg, ...)
    testing/           Mock transport factory + pytest fixtures

tools/
  generate_models.py      Fetch OpenAPI spec and generate HTTP models
  generate_ws_models.py   Fetch AsyncAPI spec and generate WebSocket models
  sync_docstrings.py      Sync API function docstrings from OpenAPI spec
```

## Tooling

The `tools/` directory contains scripts that sync parts of the codebase with the Kalshi OpenAPI spec:

```bash
# Regenerate HTTP models (enums, core objects, requests, responses)
uv run python tools/generate_models.py

# Regenerate WebSocket models (Channel enum, message types)
uv run python tools/generate_ws_models.py

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

async def fetch_balance(client: KalshiHttpClientProtocol) -> int:
    result = await client.get_balance()
    return result.balance  # typed attribute access
```

### WebSocket

```python
from pykalshi import KalshiWebSocketClientProtocol

async def subscribe_orderbook(ws: KalshiWebSocketClientProtocol, ticker: str) -> None:
    await ws.add_market(ticker, ["orderbook_delta"])
```

This enables mocking and swapping implementations freely. The library includes a `py.typed` marker (PEP 561) for full type checking support.
