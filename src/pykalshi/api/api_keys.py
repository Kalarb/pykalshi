"""API Keys management methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import API_KEYS_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_api_keys(client: KalshiHttpClient) -> dict[str, Any]:
    """Get API Keys.
    
    GET /trade-api/v2/api_keys
    
    Endpoint for retrieving all API keys associated with the authenticated user.  API keys
allow programmatic access to the platform without requiring username/password
authentication. Each key has a unique identifier and name.
    """
    return await client.get(API_KEYS_URL)


async def create_api_key(
    client: KalshiHttpClient, *, public_key: str, name: str
) -> dict[str, Any]:
    """Create API Key.
    
    POST /trade-api/v2/api_keys
    
    Endpoint for creating a new API key with a user-provided public key. This endpoint
allows users to create API keys by providing their own RSA public key. The platform will
use this public key to verify signatures on API requests.
    """
    return await client.post(
        API_KEYS_URL, body={"public_key": public_key, "name": name}
    )


async def generate_api_key(
    client: KalshiHttpClient, *, name: str
) -> dict[str, Any]:
    """Generate API Key.
    
    POST /trade-api/v2/api_keys/generate
    
    Endpoint for generating a new API key with an automatically created key pair.  This
endpoint generates both a public and private RSA key pair. The public key is stored on
the platform, while the private key is returned to the user and must be stored securely.
The private key cannot be retrieved again.
    """
    return await client.post(f"{API_KEYS_URL}/generate", body={"name": name})


async def delete_api_key(
    client: KalshiHttpClient, api_key: str
) -> dict[str, Any]:
    """Delete API Key.
    
    DELETE /trade-api/v2/api_keys/{api_key}
    
    Endpoint for deleting an existing API key.  This endpoint permanently deletes an API
key. Once deleted, the key can no longer be used for authentication. This action cannot
be undone.
    """
    return await client.delete(f"{API_KEYS_URL}/{api_key}")
