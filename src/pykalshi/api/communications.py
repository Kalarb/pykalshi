"""Communications API methods (RFQs and Quotes)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import COMMUNICATIONS_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_communications_id(client: KalshiHttpClient) -> dict[str, Any]:
    """GET /trade-api/v2/communications/id"""
    return await client.get(f"{COMMUNICATIONS_URL}/id")


# --- RFQs ---


async def get_rfqs(
    client: KalshiHttpClient,
    *,
    cursor: Optional[str] = None,
    event_ticker: Optional[str] = None,
    market_ticker: Optional[str] = None,
    subaccount: Optional[int] = None,
    limit: Optional[int] = None,
    status: Optional[str] = None,
    creator_user_id: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/communications/rfqs"""
    params = strip_none({
        "cursor": cursor,
        "event_ticker": event_ticker,
        "market_ticker": market_ticker,
        "subaccount": subaccount,
        "limit": limit,
        "status": status,
        "creator_user_id": creator_user_id,
    })
    return await client.get(f"{COMMUNICATIONS_URL}/rfqs", params=params)


async def create_rfq(
    client: KalshiHttpClient,
    *,
    market_ticker: str,
    side: str,
    size: int,
    price: Optional[str] = None,
    counterparty_user_id: Optional[str] = None,
) -> dict[str, Any]:
    """POST /trade-api/v2/communications/rfqs"""
    payload = strip_none({
        "market_ticker": market_ticker,
        "side": side,
        "size": size,
        "price": price,
        "counterparty_user_id": counterparty_user_id,
    })
    return await client.post(f"{COMMUNICATIONS_URL}/rfqs", body=payload)


async def get_rfq(
    client: KalshiHttpClient, rfq_id: str
) -> dict[str, Any]:
    """GET /trade-api/v2/communications/rfqs/{rfq_id}"""
    return await client.get(f"{COMMUNICATIONS_URL}/rfqs/{rfq_id}")


async def delete_rfq(
    client: KalshiHttpClient, rfq_id: str
) -> dict[str, Any]:
    """DELETE /trade-api/v2/communications/rfqs/{rfq_id}"""
    return await client.delete(f"{COMMUNICATIONS_URL}/rfqs/{rfq_id}")


# --- Quotes ---


async def get_quotes(
    client: KalshiHttpClient,
    *,
    cursor: Optional[str] = None,
    event_ticker: Optional[str] = None,
    market_ticker: Optional[str] = None,
    limit: Optional[int] = None,
    status: Optional[str] = None,
    quote_creator_user_id: Optional[str] = None,
    rfq_creator_user_id: Optional[str] = None,
    rfq_creator_subtrader_id: Optional[str] = None,
    rfq_id: Optional[str] = None,
) -> dict[str, Any]:
    """GET /trade-api/v2/communications/quotes"""
    params = strip_none({
        "cursor": cursor,
        "event_ticker": event_ticker,
        "market_ticker": market_ticker,
        "limit": limit,
        "status": status,
        "quote_creator_user_id": quote_creator_user_id,
        "rfq_creator_user_id": rfq_creator_user_id,
        "rfq_creator_subtrader_id": rfq_creator_subtrader_id,
        "rfq_id": rfq_id,
    })
    return await client.get(f"{COMMUNICATIONS_URL}/quotes", params=params)


async def create_quote(
    client: KalshiHttpClient,
    *,
    rfq_id: str,
    price: str,
    size: int,
) -> dict[str, Any]:
    """POST /trade-api/v2/communications/quotes"""
    return await client.post(
        f"{COMMUNICATIONS_URL}/quotes",
        body={"rfq_id": rfq_id, "price": price, "size": size},
    )


async def get_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """GET /trade-api/v2/communications/quotes/{quote_id}"""
    return await client.get(f"{COMMUNICATIONS_URL}/quotes/{quote_id}")


async def delete_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """DELETE /trade-api/v2/communications/quotes/{quote_id}"""
    return await client.delete(f"{COMMUNICATIONS_URL}/quotes/{quote_id}")


async def accept_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """PUT /trade-api/v2/communications/quotes/{quote_id}/accept"""
    return await client.put(
        f"{COMMUNICATIONS_URL}/quotes/{quote_id}/accept", body={}
    )
