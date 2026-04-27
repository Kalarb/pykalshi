"""Exchange API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._utils import EXCHANGE_URL

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_exchange_status(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Exchange Status.
    
    GET /trade-api/v2/exchange/status
    
    Endpoint for getting the exchange status.
    """
    return await client.get(f"{EXCHANGE_URL}/status")


async def get_exchange_schedule(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Exchange Schedule.
    
    GET /trade-api/v2/exchange/schedule
    
    Endpoint for getting the exchange schedule.
    """
    return await client.get(f"{EXCHANGE_URL}/schedule")


async def get_exchange_announcements(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Exchange Announcements.
    
    GET /trade-api/v2/exchange/announcements
    
    Endpoint for getting all exchange-wide announcements.
    """
    return await client.get(f"{EXCHANGE_URL}/announcements")


async def get_user_data_timestamp(client: KalshiHttpClient) -> dict[str, Any]:
    """Get User Data Timestamp.
    
    GET /trade-api/v2/exchange/user_data_timestamp
    
    There is typically a short delay before exchange events are reflected in the API
endpoints. Whenever possible, combine API responses to PUT/POST/DELETE requests with
websocket data to obtain the most accurate view of the exchange state. This endpoint
provides an approximate indication of when the data from the following endpoints was
last validated: GetBalance, GetOrder(s), GetFills, GetPositions
    """
    return await client.get(f"{EXCHANGE_URL}/user_data_timestamp")
