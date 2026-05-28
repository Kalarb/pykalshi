# Changelog

## 0.5.0 — Initial Open-Source Release

- Async HTTP client (KalshiHttpClient) — 50+ endpoints across 23 API domains
- Async WebSocket client (KalshiWebSocketClient) — 11+ subscription channels
- 144 typed Pydantic v2 models (auto-generated from OpenAPI/AsyncAPI specs)
- RSA-PSS authentication
- Read/write rate limiting with token bucket
- Exponential backoff retry for 429s and network errors
- Optional OpenTelemetry instrumentation
- Protocol-based typed contracts for testing
- Mock transport factory + pytest fixtures
