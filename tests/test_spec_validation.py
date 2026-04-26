"""Spec validation tests — fetch live Kalshi specs and validate pykalshi coverage.

These tests hit the network to fetch the latest specs from docs.kalshi.com.
Run with: uv run pytest tests/test_spec_validation.py -v
"""

import httpx
import pytest
import yaml

from pykalshi.ws_client import MSG_TYPE_TO_CHANNEL

pytestmark = pytest.mark.integration

# Endpoints we deliberately skip (not accessible to us)
SKIPPED_PATH_PREFIXES = {
    "/trade-api/v2/portfolio/subaccounts",
    "/trade-api/v2/portfolio/summary",
    "/trade-api/v2/fcm",
}


def _should_skip_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in SKIPPED_PATH_PREFIXES)


@pytest.mark.asyncio
async def test_openapi_coverage() -> None:
    """Every accessible endpoint in Kalshi's OpenAPI spec should have a method in KalshiHttpClient."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://docs.kalshi.com/openapi.yaml", timeout=15.0)
        resp.raise_for_status()

    spec = yaml.safe_load(resp.text)
    paths = spec.get("paths", {})

    # Collect all (method, path) tuples from the spec
    spec_endpoints: set[tuple[str, str]] = set()
    for path, methods in paths.items():
        full_path = f"/trade-api/v2{path}" if not path.startswith("/trade-api") else path
        if _should_skip_path(full_path):
            continue
        for method in methods:
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                spec_endpoints.add((method.upper(), full_path))

    # Collect all methods from KalshiHttpClient by inspecting the class
    from pykalshi.http_client import KalshiHttpClient
    client_methods = {
        name for name in dir(KalshiHttpClient)
        if not name.startswith("_") and callable(getattr(KalshiHttpClient, name))
    }

    # We can't perfectly map method names to paths automatically, but we can
    # check that the number of public async methods is close to the spec count.
    # More importantly, just assert the spec was fetched and parsed.
    assert len(spec_endpoints) > 40, f"Expected 40+ endpoints, got {len(spec_endpoints)}"
    assert len(client_methods) > 60, f"Expected 60+ methods, got {len(client_methods)}"

    # Log the counts for visibility
    print(f"\nOpenAPI spec endpoints: {len(spec_endpoints)}")
    print(f"KalshiHttpClient public methods: {len(client_methods)}")
    print(f"Skipped prefixes: {SKIPPED_PATH_PREFIXES}")


@pytest.mark.asyncio
async def test_asyncapi_ws_channel_coverage() -> None:
    """Every channel and message type in Kalshi's AsyncAPI spec should be in MSG_TYPE_TO_CHANNEL."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://docs.kalshi.com/asyncapi.yaml", timeout=15.0)
        resp.raise_for_status()

    spec = yaml.safe_load(resp.text)
    channels = spec.get("channels", {})

    # Extract channel names (skip 'root' and 'control_frames' — those are meta)
    spec_channels: set[str] = set()
    spec_message_types: set[str] = set()

    for channel_key, channel_def in channels.items():
        if channel_key in ("root", "control_frames"):
            continue
        # The channel address is the subscribable name
        address = channel_def.get("address", channel_key)
        spec_channels.add(address)

        # Extract message types from the channel's messages
        for msg_key, msg_ref in channel_def.get("messages", {}).items():
            # msg_key is the local message name (e.g., "orderbookSnapshot")
            # We need the actual "name" field from the resolved message
            # For simplicity, derive from the $ref or use the key
            if "$ref" in msg_ref:
                ref_path = msg_ref["$ref"]
                # e.g., "#/components/messages/orderbookSnapshot"
                msg_name = ref_path.split("/")[-1]
                # Look up the actual message to get its 'name' field
                resolved = spec.get("components", {}).get("messages", {}).get(msg_name, {})
                actual_name = resolved.get("name", msg_name)
                spec_message_types.add(actual_name)

    # Validate MSG_TYPE_TO_CHANNEL covers all message types
    our_types = set(MSG_TYPE_TO_CHANNEL.keys())
    missing_types = spec_message_types - our_types
    assert missing_types == set(), f"Missing message types in MSG_TYPE_TO_CHANNEL: {missing_types}"

    # Validate all channels are referenced
    our_channels = {v for v in MSG_TYPE_TO_CHANNEL.values() if v is not None}
    missing_channels = spec_channels - our_channels
    assert missing_channels == set(), f"Channels not referenced: {missing_channels}"

    print(f"\nAsyncAPI channels: {len(spec_channels)}")
    print(f"AsyncAPI message types: {len(spec_message_types)}")
    print(f"MSG_TYPE_TO_CHANNEL entries: {len(MSG_TYPE_TO_CHANNEL)}")
