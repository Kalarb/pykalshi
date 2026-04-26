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
