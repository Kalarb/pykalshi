"""Exchange API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import EXCHANGE_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_exchange_status(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/exchange/status"""
    return await client.get(f"{EXCHANGE_URL}/status")


async def get_exchange_schedule(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/exchange/schedule"""
    return await client.get(f"{EXCHANGE_URL}/schedule")
