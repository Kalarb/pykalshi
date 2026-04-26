"""Tests for pykalshi.auth."""

import tempfile

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from pykalshi.auth import KalshiCredentials
from pykalshi.exceptions import KalshiAuthError


def _generate_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("utf-8")


class TestKalshiCredentials:
    def test_from_pem_string(self) -> None:
        pem = _generate_pem()
        creds = KalshiCredentials.from_pem_string("test-key", pem)
        assert creds.key_id == "test-key"
        assert creds.private_key is not None

    def test_from_key_file(self, tmp_path: object) -> None:
        pem = _generate_pem()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".pem", delete=False
        ) as f:
            f.write(pem)
            f.flush()
            creds = KalshiCredentials.from_key_file("test-key", f.name)
        assert creds.key_id == "test-key"

    def test_from_private_key(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        creds = KalshiCredentials.from_private_key("test-key", key)
        assert creds.key_id == "test-key"
        assert creds.private_key is key

    def test_from_key_file_not_found(self) -> None:
        with pytest.raises(KalshiAuthError, match="not found"):
            KalshiCredentials.from_key_file("test-key", "/nonexistent/path.pem")

    def test_from_pem_string_invalid(self) -> None:
        with pytest.raises(KalshiAuthError, match="Failed to load"):
            KalshiCredentials.from_pem_string("test-key", "not a pem")

    def test_auth_headers(self) -> None:
        pem = _generate_pem()
        creds = KalshiCredentials.from_pem_string("my-key-id", pem)
        headers = creds.auth_headers("GET", "/trade-api/v2/exchange/status")

        assert headers["KALSHI-ACCESS-KEY"] == "my-key-id"
        assert "KALSHI-ACCESS-SIGNATURE" in headers
        assert "KALSHI-ACCESS-TIMESTAMP" in headers
        assert headers["Content-Type"] == "application/json"

    def test_auth_headers_strips_query_string(self) -> None:
        pem = _generate_pem()
        creds = KalshiCredentials.from_pem_string("key", pem)
        h1 = creds.auth_headers("GET", "/api/v2/markets?limit=100")
        h2 = creds.auth_headers("GET", "/api/v2/markets")
        # Both should sign the same path (without query string)
        # Signatures differ due to timestamp, but both should succeed
        assert h1["KALSHI-ACCESS-KEY"] == h2["KALSHI-ACCESS-KEY"]

    def test_sign_pss_text(self) -> None:
        pem = _generate_pem()
        creds = KalshiCredentials.from_pem_string("key", pem)
        sig = creds.sign_pss_text("hello world")
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_frozen(self) -> None:
        pem = _generate_pem()
        creds = KalshiCredentials.from_pem_string("key", pem)
        with pytest.raises(AttributeError):
            creds.key_id = "other"  # type: ignore[misc]
