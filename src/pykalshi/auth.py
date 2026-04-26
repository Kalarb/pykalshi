"""RSA-PSS authentication for the Kalshi API."""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature

from .exceptions import KalshiAuthError


@dataclass(frozen=True)
class KalshiCredentials:
    """Immutable credential holder for Kalshi API authentication.

    Supports three construction modes: file path, PEM string, or pre-loaded key.
    """

    key_id: str
    private_key: rsa.RSAPrivateKey

    @classmethod
    def from_key_file(cls, key_id: str, path: str) -> KalshiCredentials:
        """Load credentials from an RSA private key file."""
        resolved = os.path.abspath(os.path.expanduser(path))
        try:
            with open(resolved, "rb") as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
        except FileNotFoundError:
            raise KalshiAuthError(f"Private key file not found at: {resolved}")
        except Exception as e:
            raise KalshiAuthError(f"Failed to load private key from {resolved}: {e}") from e
        if not isinstance(key, rsa.RSAPrivateKey):
            raise KalshiAuthError(f"Key at {resolved} is not an RSA private key")
        return cls(key_id=key_id, private_key=key)

    @classmethod
    def from_pem_string(cls, key_id: str, pem: str) -> KalshiCredentials:
        """Load credentials from a PEM-encoded string."""
        try:
            key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
        except Exception as e:
            raise KalshiAuthError(f"Failed to load private key from PEM string: {e}") from e
        if not isinstance(key, rsa.RSAPrivateKey):
            raise KalshiAuthError("Provided PEM is not an RSA private key")
        return cls(key_id=key_id, private_key=key)

    @classmethod
    def from_private_key(cls, key_id: str, key: rsa.RSAPrivateKey) -> KalshiCredentials:
        """Create credentials from a pre-loaded RSA private key."""
        return cls(key_id=key_id, private_key=key)

    def sign_pss_text(self, text: str) -> str:
        """Sign text using RSA-PSS with SHA256."""
        message = text.encode("utf-8")
        try:
            signature = self.private_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH,
                ),
                hashes.SHA256(),
            )
            return base64.b64encode(signature).decode("utf-8")
        except InvalidSignature as e:
            raise KalshiAuthError("RSA-PSS signing failed") from e

    def auth_headers(self, method: str, path: str) -> dict[str, str]:
        """Generate Kalshi authentication headers for a request."""
        timestamp_ms = str(int(time.time() * 1000))
        path_no_query = path.split("?", 1)[0]
        msg_string = timestamp_ms + method.upper() + path_no_query
        signature = self.sign_pss_text(msg_string)
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
        }
