"""Communications API methods (RFQs and Quotes)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import COMMUNICATIONS_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_communications_id(client: KalshiHttpClient) -> dict[str, Any]:
    """Get Communications ID.
    
    GET /trade-api/v2/communications/id
    
    Endpoint for getting the communications ID of the logged-in user.
    """
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
    """Get RFQs.
    
    GET /trade-api/v2/communications/rfqs
    
    Endpoint for getting RFQs
    """
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
    """Create RFQ.
    
    POST /trade-api/v2/communications/rfqs
    
    Endpoint for creating a new RFQ. You can have a maximum of 100 open RFQs at a time.
    """
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
    """Get RFQ.
    
    GET /trade-api/v2/communications/rfqs/{rfq_id}
    
    Endpoint for getting a single RFQ by id
    """
    return await client.get(f"{COMMUNICATIONS_URL}/rfqs/{rfq_id}")


async def delete_rfq(
    client: KalshiHttpClient, rfq_id: str
) -> dict[str, Any]:
    """Delete RFQ.
    
    DELETE /trade-api/v2/communications/rfqs/{rfq_id}
    
    Endpoint for deleting an RFQ by ID
    """
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
    """Get Quotes.
    
    GET /trade-api/v2/communications/quotes
    
    Endpoint for getting quotes
    """
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
    """Create Quote.
    
    POST /trade-api/v2/communications/quotes
    
    Endpoint for creating a quote in response to an RFQ
    """
    return await client.post(
        f"{COMMUNICATIONS_URL}/quotes",
        body={"rfq_id": rfq_id, "price": price, "size": size},
    )


async def get_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """Get Quote.
    
    GET /trade-api/v2/communications/quotes/{quote_id}
    
    Endpoint for getting a particular quote
    """
    return await client.get(f"{COMMUNICATIONS_URL}/quotes/{quote_id}")


async def delete_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """Delete Quote.
    
    DELETE /trade-api/v2/communications/quotes/{quote_id}
    
    Endpoint for deleting a quote, which means it can no longer be accepted.
    """
    return await client.delete(f"{COMMUNICATIONS_URL}/quotes/{quote_id}")


async def confirm_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """Confirm Quote.

    PUT /trade-api/v2/communications/quotes/{quote_id}/confirm

    Endpoint for confirming a quote.
    """
    return await client.put(
        f"{COMMUNICATIONS_URL}/quotes/{quote_id}/confirm", body={}
    )


async def accept_quote(
    client: KalshiHttpClient, quote_id: str
) -> dict[str, Any]:
    """Accept Quote.
    
    PUT /trade-api/v2/communications/quotes/{quote_id}/accept
    
    Endpoint for accepting a quote. This will require the quoter to confirm
    """
    return await client.put(
        f"{COMMUNICATIONS_URL}/quotes/{quote_id}/accept", body={}
    )
