"""AsyncAPI spec validation — fetch live spec and validate WS channel coverage.

Fetches https://docs.kalshi.com/asyncapi.yaml and asserts pykalshi's
MSG_TYPE_TO_CHANNEL covers all channels and message types.

Run with: uv run pytest tests/test_asyncapi_validation.py -v
"""

import httpx
import pytest
import yaml

from pykalshi.ws_client import MSG_TYPE_TO_CHANNEL

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_asyncapi_ws_channel_coverage() -> None:
    """Every channel and message type in Kalshi's AsyncAPI spec should be in MSG_TYPE_TO_CHANNEL."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://docs.kalshi.com/asyncapi.yaml", timeout=15.0)
        resp.raise_for_status()

    spec = yaml.safe_load(resp.text)
    channels = spec.get("channels", {})

    spec_channels: set[str] = set()
    spec_message_types: set[str] = set()

    for channel_key, channel_def in channels.items():
        if channel_key in ("root", "control_frames"):
            continue
        address = channel_def.get("address", channel_key)
        spec_channels.add(address)

        for msg_key, msg_ref in channel_def.get("messages", {}).items():
            if "$ref" in msg_ref:
                ref_path = msg_ref["$ref"]
                msg_name = ref_path.split("/")[-1]
                resolved = spec.get("components", {}).get("messages", {}).get(msg_name, {})
                actual_name = resolved.get("name", msg_name)
                spec_message_types.add(actual_name)

    our_types = set(MSG_TYPE_TO_CHANNEL.keys())
    missing_types = spec_message_types - our_types
    assert missing_types == set(), f"Missing message types in MSG_TYPE_TO_CHANNEL: {missing_types}"

    our_channels = {v for v in MSG_TYPE_TO_CHANNEL.values() if v is not None}
    missing_channels = spec_channels - our_channels
    assert missing_channels == set(), f"Channels not referenced: {missing_channels}"

    print(f"\nAsyncAPI channels: {len(spec_channels)}")
    print(f"AsyncAPI message types: {len(spec_message_types)}")
    print(f"MSG_TYPE_TO_CHANNEL entries: {len(MSG_TYPE_TO_CHANNEL)}")
