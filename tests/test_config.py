"""Unit tests for config.py — URL resolution, defaults, immutability."""

from __future__ import annotations

import pytest

from pykalshi.config import ClientConfig, Environment


class TestClientConfigDefaults:
    def test_default_environment(self) -> None:
        cfg = ClientConfig()
        assert cfg.environment == Environment.DEMO

    def test_default_rates(self) -> None:
        cfg = ClientConfig()
        assert cfg.read_rate == 20.0
        assert cfg.write_rate == 10.0

    def test_default_timeouts(self) -> None:
        cfg = ClientConfig()
        assert cfg.connect_timeout == 5.0
        assert cfg.read_timeout == 30.0
        assert cfg.write_timeout == 10.0
        assert cfg.pool_timeout == 5.0

    def test_default_retry(self) -> None:
        cfg = ClientConfig()
        assert cfg.max_retries == 4
        assert cfg.base_retry_delay == 0.1


class TestUrlResolution:
    def test_http_url_from_environment_demo(self) -> None:
        cfg = ClientConfig(environment=Environment.DEMO)
        assert cfg.resolved_http_url == "https://external-api.demo.kalshi.co"

    def test_http_url_from_environment_prod(self) -> None:
        cfg = ClientConfig(environment=Environment.PROD)
        assert cfg.resolved_http_url == "https://external-api.kalshi.com"

    def test_ws_url_from_environment_demo(self) -> None:
        cfg = ClientConfig(environment=Environment.DEMO)
        assert cfg.resolved_ws_url == "wss://external-api-ws.demo.kalshi.co"

    def test_ws_url_from_environment_prod(self) -> None:
        cfg = ClientConfig(environment=Environment.PROD)
        assert cfg.resolved_ws_url == "wss://external-api-ws.kalshi.com"

    def test_explicit_http_url_takes_precedence(self) -> None:
        cfg = ClientConfig(http_base_url="https://custom.example.com")
        assert cfg.resolved_http_url == "https://custom.example.com"

    def test_explicit_ws_url_takes_precedence(self) -> None:
        cfg = ClientConfig(ws_base_url="wss://custom.example.com")
        assert cfg.resolved_ws_url == "wss://custom.example.com"

    def test_env_var_http_takes_precedence_over_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KALSHI_HTTP_BASE_URL", "https://env-override.example.com")
        cfg = ClientConfig()
        assert cfg.resolved_http_url == "https://env-override.example.com"

    def test_env_var_ws_takes_precedence_over_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KALSHI_WS_BASE_URL", "wss://env-override.example.com")
        cfg = ClientConfig()
        assert cfg.resolved_ws_url == "wss://env-override.example.com"

    def test_explicit_beats_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KALSHI_HTTP_BASE_URL", "https://env.example.com")
        cfg = ClientConfig(http_base_url="https://explicit.example.com")
        assert cfg.resolved_http_url == "https://explicit.example.com"


class TestImmutability:
    def test_frozen_dataclass(self) -> None:
        cfg = ClientConfig()
        with pytest.raises(AttributeError):
            cfg.read_rate = 99.0  # type: ignore[misc]
