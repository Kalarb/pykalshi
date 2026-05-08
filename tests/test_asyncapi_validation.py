"""AsyncAPI spec validation — fetch live spec and validate WS channel + schema coverage.

Fetches https://docs.kalshi.com/asyncapi.yaml and checks:
1. Every channel and message type is in MSG_TYPE_TO_CHANNEL
2. Every spec schema has a matching Pydantic model with all fields

Run with: uv run pytest tests/test_asyncapi_validation.py -v -s
"""

import httpx
import pytest
import yaml

from pykalshi.ws_client import MSG_TYPE_TO_CHANNEL
import pykalshi.models.ws as ws_models

pytestmark = pytest.mark.integration

# Matches generate_ws_models.py
_TYPE_ALIASES = {"commandId", "subscriptionId", "sequenceNumber", "marketId", "marketTicker", "marketSide", "orderAction"}
_SKIP_CHANNELS = {"root", "control_frames"}
_RESERVED_WORDS = {"type": "type_", "class": "class_"}


def _to_class_name(schema_name: str) -> str:
    """Capitalize first letter (matches generate_ws_models.py to_class_name)."""
    return schema_name[0].upper() + schema_name[1:]


def _spec_field_to_model_field(field_name: str) -> str:
    return _RESERVED_WORDS.get(field_name, field_name)


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
        if channel_key in _SKIP_CHANNELS:
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


@pytest.mark.asyncio
async def test_asyncapi_schema_coverage() -> None:
    """Every AsyncAPI schema should have a matching Pydantic model with all fields."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://docs.kalshi.com/asyncapi.yaml", timeout=15.0)
        resp.raise_for_status()

    spec = yaml.safe_load(resp.text)
    schemas = spec.get("components", {}).get("schemas", {})

    missing_models: list[str] = []
    missing_fields: list[str] = []

    for schema_name, schema in sorted(schemas.items()):
        if schema_name in _TYPE_ALIASES:
            continue
        if schema.get("type") != "object":
            continue

        class_name = _to_class_name(schema_name)
        model_cls = getattr(ws_models, class_name, None)

        if model_cls is None:
            missing_models.append(f"{schema_name} (expected {class_name})")
            continue

        spec_props = schema.get("properties", {})
        if not spec_props:
            continue

        model_fields = set(model_cls.model_fields.keys()) if hasattr(model_cls, "model_fields") else set()

        for prop_name, prop_schema in spec_props.items():
            if prop_schema.get("deprecated", False):
                continue
            if not prop_name.isidentifier():
                continue

            expected_field = _spec_field_to_model_field(prop_name)

            # For inline msg objects, also check the *Msg class
            if prop_name == "msg" and prop_schema.get("type") == "object" and prop_schema.get("properties"):
                msg_class_name = class_name.replace("Payload", "Msg")
                msg_cls = getattr(ws_models, msg_class_name, None)
                if msg_cls is None:
                    missing_models.append(f"{schema_name}.msg (expected {msg_class_name})")
                else:
                    msg_model_fields = set(msg_cls.model_fields.keys())
                    for msg_prop_name, msg_prop_schema in prop_schema.get("properties", {}).items():
                        if msg_prop_schema.get("deprecated", False):
                            continue
                        if not msg_prop_name.isidentifier():
                            continue
                        msg_expected = _spec_field_to_model_field(msg_prop_name)
                        if msg_expected not in msg_model_fields:
                            missing_fields.append(f"{msg_class_name}.{msg_prop_name}")
                continue

            if expected_field not in model_fields:
                missing_fields.append(f"{class_name}.{prop_name}")

    # --- Report ---
    print(f"\nAsyncAPI schemas checked: {len(schemas)}")

    if missing_models:
        print(f"\nMissing WS models ({len(missing_models)}):")
        for name in missing_models:
            print(f"  {name}")

    if missing_fields:
        print(f"\nMissing WS fields ({len(missing_fields)}):")
        for entry in missing_fields:
            print(f"  {entry}")

    all_gaps = missing_models + missing_fields
    assert all_gaps == [], (
        "AsyncAPI schema drift detected:\n" + "\n".join(f"  {g}" for g in all_gaps)
    )
