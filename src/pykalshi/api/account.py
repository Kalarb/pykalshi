"""Account API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import ACCOUNT_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_api_limits(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/account/limits"""
    return await client.get(f"{ACCOUNT_URL}/limits")
