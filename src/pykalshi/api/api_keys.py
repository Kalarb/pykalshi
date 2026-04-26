"""API Keys management methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import API_KEYS_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_api_keys(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/api_keys"""
    return await client.get(API_KEYS_URL)


async def create_api_key(
    client: KalshiHttpClient, *, public_key: str
) -> dict[str, Any]:
    """POST /trade-api/v2/api_keys"""
    return await client.post(API_KEYS_URL, body={"public_key": public_key})


async def generate_api_key(
    client: KalshiHttpClient, *, name: str
) -> dict[str, Any]:
    """POST /trade-api/v2/api_keys/generate"""
    return await client.post(f"{API_KEYS_URL}/generate", body={"name": name})


async def delete_api_key(
    client: KalshiHttpClient, api_key: str
) -> dict[str, Any]:
    """DELETE /trade-api/v2/api_keys/{api_key}"""
    return await client.delete(f"{API_KEYS_URL}/{api_key}")
