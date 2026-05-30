"""Live data API methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ._utils import LIVE_DATA_URL, strip_none

if TYPE_CHECKING:
    from pykalshi.http_client import KalshiHttpClient


async def get_live_data(
    client: KalshiHttpClient,
    milestone_id: str,
    *,
    include_player_stats: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Live Data.
    
    GET /trade-api/v2/live_data/milestone/{milestone_id}
    
    Get live data for a specific milestone.
    """
    params = strip_none({"include_player_stats": include_player_stats})
    return await client.get(
        f"{LIVE_DATA_URL}/milestone/{milestone_id}", params=params
    )


async def get_live_data_legacy(
    client: KalshiHttpClient,
    data_type: str,
    milestone_id: str,
    *,
    include_player_stats: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Live Data (with type).
    
    GET /trade-api/v2/live_data/{type}/milestone/{milestone_id}
    
    Get live data for a specific milestone. This is the legacy endpoint that requires a type
path parameter. Prefer using `/live_data/milestone/{milestone_id}` instead.
    """
    params = strip_none({"include_player_stats": include_player_stats})
    return await client.get(
        f"{LIVE_DATA_URL}/{data_type}/milestone/{milestone_id}", params=params
    )


async def get_live_data_batch(
    client: KalshiHttpClient,
    milestone_ids: list[str],
    *,
    include_player_stats: Optional[bool] = None,
) -> dict[str, Any]:
    """Get Multiple Live Data.
    
    GET /trade-api/v2/live_data/batch
    
    Get live data for multiple milestones
    """
    params: dict[str, Any] = {"milestone_ids": ",".join(milestone_ids)}
    if include_player_stats is not None:
        params["include_player_stats"] = include_player_stats
    return await client.get(f"{LIVE_DATA_URL}/batch", params=params)


async def get_game_stats(
    client: KalshiHttpClient, milestone_id: str
) -> dict[str, Any]:
    """Get Game Stats.
    
    GET /trade-api/v2/live_data/milestone/{milestone_id}/game_stats
    
    Get play-by-play game statistics for a specific milestone. Supported sports: Pro
Football, College Football, Pro Basketball, College Men's Basketball, College Women's
Basketball, WNBA, Soccer, Pro Hockey, and Pro Baseball. Returns null for unsupported
milestone types or milestones without a Sportradar ID.
    """
    return await client.get(
        f"{LIVE_DATA_URL}/milestone/{milestone_id}/game_stats"
    )
