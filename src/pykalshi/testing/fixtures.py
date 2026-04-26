"""Reusable test fixtures for pykalshi consumers."""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric import rsa

from pykalshi.auth import KalshiCredentials
from pykalshi.config import ClientConfig, Environment


def mock_credentials() -> KalshiCredentials:
    """Generate a throwaway RSA keypair for tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return KalshiCredentials.from_private_key("test-key-id", key)


def test_config() -> ClientConfig:
    """Configuration suitable for unit tests."""
    return ClientConfig(
        environment=Environment.DEMO,
        http_base_url="http://localhost:0",
        ws_base_url="ws://localhost:0",
    )
