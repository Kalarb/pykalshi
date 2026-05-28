[![PyPI](https://img.shields.io/pypi/v/pykalshi-client)](https://pypi.org/project/pykalshi-client/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/Kalarb/pykalshi/blob/main/LICENSE)
[![CI](https://github.com/Kalarb/pykalshi/actions/workflows/ci.yml/badge.svg)](https://github.com/Kalarb/pykalshi/actions/workflows/ci.yml)
[![OpenAPI](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/yardboy27/65579a629076066fcbf09520ca76301a/raw/openapi-status.json)](https://github.com/Kalarb/pykalshi/actions/workflows/openapi-validation.yml)
[![AsyncAPI](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/yardboy27/65579a629076066fcbf09520ca76301a/raw/asyncapi-status.json)](https://github.com/Kalarb/pykalshi/actions/workflows/asyncapi-validation.yml)

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
| `read_rate` | 20.0 | Fallback read token rate (auto-configured from API on first request) |
| `write_rate` | 10.0 | Fallback write token rate (auto-configured from API on first request) |
| `auto_configure_rates` | `True` | Fetch actual rate limits and per-endpoint costs from `/account/limits` and `/account/endpoint_costs` on first request. Set `False` to use fallback values only. |
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

## API Coverage

See [API Coverage](https://github.com/Kalarb/pykalshi/blob/main/docs/API_COVERAGE.md) for per-endpoint test coverage (auto-updated by CI on every push to main).

**Skipped** (not accessible): subaccounts, FCM, summary/resting_order_value.

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
