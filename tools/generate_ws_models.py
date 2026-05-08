#!/usr/bin/env python3
"""Generate Pydantic v2 models from the Kalshi AsyncAPI spec (WebSocket messages).

Usage:
    uv run python tools/generate_ws_models.py

Fetches https://docs.kalshi.com/asyncapi.yaml, parses all component schemas,
and writes typed WS message models to src/pykalshi/models/ws.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import yaml

SPEC_URL = "https://docs.kalshi.com/asyncapi.yaml"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "pykalshi" / "models"

# Simple type alias schemas — map to Python types instead of full models
TYPE_ALIASES: dict[str, str] = {
    "commandId": "int",
    "subscriptionId": "int",
    "sequenceNumber": "int",
    "marketId": "str",
    "marketTicker": "str",
    "marketSide": "str",
    "orderAction": "str",
    "bookSide": "str",
}


def fetch_spec() -> dict[str, Any]:
    print(f"Fetching {SPEC_URL}...")
    resp = httpx.get(SPEC_URL, timeout=15.0)
    resp.raise_for_status()
    spec = yaml.safe_load(resp.text)
    print(f"  Loaded {len(spec.get('components', {}).get('schemas', {}))} schemas")
    return spec


def ref_to_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def resolve_type(prop: dict[str, Any], required: bool) -> str:
    """Convert an AsyncAPI property schema to a Python type annotation."""
    nullable = prop.get("nullable", False)

    # Handle allOf wrapper
    if "allOf" in prop and len(prop["allOf"]) == 1:
        inner = {**prop["allOf"][0], **{k: v for k, v in prop.items() if k != "allOf"}}
        return resolve_type(inner, required)

    if "$ref" in prop:
        ref_name = ref_to_name(prop["$ref"])
        py_type = TYPE_ALIASES.get(ref_name, ref_name)
    elif prop.get("const") is not None:
        py_type = "str"
    elif prop.get("type") == "string":
        py_type = "str"
    elif prop.get("type") == "integer":
        py_type = "int"
    elif prop.get("type") == "number":
        py_type = "float"
    elif prop.get("type") == "boolean":
        py_type = "bool"
    elif prop.get("type") == "array":
        items = prop.get("items", {})
        item_type = resolve_type(items, required=True)
        py_type = f"list[{item_type}]"
    elif prop.get("type") == "object":
        additional = prop.get("additionalProperties")
        if isinstance(additional, dict):
            val_type = resolve_type(additional, required=True)
            py_type = f"dict[str, {val_type}]"
        elif additional is True:
            py_type = "dict[str, Any]"
        elif prop.get("properties"):
            # Inline nested object — we'll handle this separately
            py_type = "dict[str, Any]"
        else:
            py_type = "dict[str, Any]"
    else:
        py_type = "Any"

    if nullable or not required:
        return f"{py_type} | None"
    return py_type


def generate_inline_model(
    class_name: str, schema: dict[str, Any]
) -> str:
    """Generate a Pydantic model from an inline object schema (the 'msg' field)."""
    properties = schema.get("properties", {})
    required_set = set(schema.get("required", []))

    lines = [f"class {class_name}(BaseModel):"]
    lines.append('    model_config = ConfigDict(extra="ignore", populate_by_name=True)')
    lines.append("")

    if not properties:
        lines.append("    pass")
        return "\n".join(lines)

    for prop_name, prop_schema in properties.items():
        if prop_schema.get("deprecated", False):
            continue

        # Skip properties with non-identifier names (e.g., numeric error codes)
        if not prop_name.isidentifier():
            continue

        is_required = prop_name in required_set
        py_type = resolve_type(prop_schema, required=is_required)
        description = prop_schema.get("description", "").strip()

        if description:
            description = description.replace("\\", "\\\\").replace('"', '\\"')
            # Collapse multi-line descriptions
            description = " ".join(description.splitlines()).strip()

        field_name = prop_name
        is_alias = prop_name in ("type", "class")
        if prop_name == "type":
            field_name = "type_"
        elif prop_name == "class":
            field_name = "class_"

        default = "" if (is_required and "| None" not in py_type) else " = None"

        if is_alias or description:
            default_val = default.strip(" =") or "..."
            field_kwargs = [default_val]
            if is_alias:
                field_kwargs.append(f'alias="{prop_name}"')
            if description:
                field_kwargs.append(f'description="{description}"')
            lines.append(f"    {field_name}: {py_type} = Field({', '.join(field_kwargs)})")
        else:
            lines.append(f"    {field_name}: {py_type}{default}")

    return "\n".join(lines)


def to_class_name(schema_name: str) -> str:
    """Convert schema name like 'orderbookSnapshotPayload' to 'OrderbookSnapshotPayload'."""
    return schema_name[0].upper() + schema_name[1:]


SKIP_CHANNELS = {"root", "control_frames"}


def generate_channel_enum(channels: dict[str, Any]) -> tuple[str, list[str]]:
    """Generate a Channel str enum from AsyncAPI channels. Returns (code, member_names)."""
    lines = [
        "class Channel(str, Enum):",
        '    """WebSocket subscription channels."""',
        "",
    ]

    member_names: list[str] = []
    for name, ch in channels.items():
        if name in SKIP_CHANNELS:
            continue

        member_name = name.upper()
        description = ch.get("description", "").strip()
        # Take first paragraph only for brevity
        if description:
            first_para = description.split("\n\n")[0].strip()
            # Collapse to single line
            first_para = " ".join(first_para.splitlines()).strip()
        else:
            first_para = ""

        lines.append(f'    {member_name} = "{name}"')
        if first_para:
            lines.append(f'    """{first_para}"""')
        lines.append("")

        member_names.append(member_name)

    return "\n".join(lines), member_names


def generate_ws_models(schemas: dict[str, Any], channels: dict[str, Any]) -> str:
    """Generate the ws.py file content."""
    lines = [
        '"""WebSocket message models generated from the Kalshi AsyncAPI spec."""',
        "",
        "# NOTE: Auto-generated by tools/generate_ws_models.py — do not edit manually.",
        "",
        "from __future__ import annotations",
        "",
        "from enum import Enum",
        "from typing import Any",
        "",
        "from pydantic import BaseModel, ConfigDict, Field",
        "",
        "",
    ]

    # Generate Channel enum first
    channel_enum, _ = generate_channel_enum(channels)
    lines.append(channel_enum)
    lines.append("")
    lines.append("")

    # Separate payload schemas (objects) from command/response schemas
    # Generate msg inner models first, then envelope models
    generated_msg_classes: list[str] = []
    generated_envelope_classes: list[str] = []
    all_class_names: list[str] = []

    for schema_name, schema in sorted(schemas.items()):
        if schema_name in TYPE_ALIASES:
            continue

        if schema.get("type") != "object":
            continue

        props = schema.get("properties", {})
        class_name = to_class_name(schema_name)

        # Check if this schema has a nested 'msg' object
        msg_prop = props.get("msg", {})
        msg_is_inline_object = (
            msg_prop.get("type") == "object" and msg_prop.get("properties")
        )

        if msg_is_inline_object:
            # Generate a separate class for the msg payload
            msg_class_name = class_name.replace("Payload", "Msg")
            msg_model = generate_inline_model(msg_class_name, msg_prop)
            generated_msg_classes.append(msg_model)
            all_class_names.append(msg_class_name)

        # Generate the envelope model
        required_set = set(schema.get("required", []))
        envelope_lines = [f"class {class_name}(BaseModel):"]

        desc = schema.get("description", "").strip()
        if desc:
            desc = desc.replace("\\", "\\\\").replace('"', '\\"')
            envelope_lines.append(f'    """{" ".join(desc.splitlines()).strip()}"""')
            envelope_lines.append("")

        envelope_lines.append('    model_config = ConfigDict(extra="ignore", populate_by_name=True)')
        envelope_lines.append("")

        if not props:
            envelope_lines.append("    pass")
        else:
            for prop_name, prop_schema in props.items():
                if prop_schema.get("deprecated", False):
                    continue

                # Skip properties with non-identifier names (e.g., numeric error codes)
                if not prop_name.isidentifier():
                    continue

                is_required = prop_name in required_set

                # Special handling for 'msg' field with inline object
                if prop_name == "msg" and msg_is_inline_object:
                    msg_class_ref = class_name.replace("Payload", "Msg")
                    py_type = msg_class_ref if is_required else f"{msg_class_ref} | None"
                    description = prop_schema.get("description", "").strip()
                    if description:
                        description = description.replace('"', '\\"')
                        envelope_lines.append(f'    msg: {py_type} = Field(..., description="{description}")')
                    else:
                        envelope_lines.append(f"    msg: {py_type}")
                    continue

                py_type = resolve_type(prop_schema, required=is_required)
                description = prop_schema.get("description", "").strip()
                if description:
                    description = description.replace("\\", "\\\\").replace('"', '\\"')
                    description = " ".join(description.splitlines()).strip()

                field_name = prop_name
                is_alias = prop_name in ("type", "class")
                if prop_name == "type":
                    field_name = "type_"
                elif prop_name == "class":
                    field_name = "class_"

                default = "" if (is_required and "| None" not in py_type) else " = None"

                if is_alias or description:
                    default_val = default.strip(" =") or "..."
                    field_kwargs = [default_val]
                    if is_alias:
                        field_kwargs.append(f'alias="{prop_name}"')
                    if description:
                        field_kwargs.append(f'description="{description}"')
                    envelope_lines.append(f"    {field_name}: {py_type} = Field({', '.join(field_kwargs)})")
                else:
                    envelope_lines.append(f"    {field_name}: {py_type}{default}")

        generated_envelope_classes.append("\n".join(envelope_lines))
        all_class_names.append(class_name)

    # Assemble: msg classes first, then envelope classes
    for cls in generated_msg_classes:
        lines.append(cls)
        lines.append("")
        lines.append("")

    for cls in generated_envelope_classes:
        lines.append(cls)
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def update_init(ws_class_names: list[str]) -> None:
    """Append WS model imports to __init__.py if not already present."""
    init_path = OUTPUT_DIR / "__init__.py"
    content = init_path.read_text()

    # Check if ws imports already exist
    if "from .ws import" in content:
        # Replace existing ws import line
        new_lines = []
        for line in content.splitlines():
            if line.startswith("from .ws import"):
                continue
            new_lines.append(line)
        content = "\n".join(new_lines)

    # Find __all__ and add ws names
    if "from .ws import" not in content:
        # Add import before __all__
        import_line = f"from .ws import {', '.join(sorted(ws_class_names))}"

        # Insert before __all__
        if "__all__" in content:
            content = content.replace("__all__", f"{import_line}\n\n__all__")
        else:
            content += f"\n{import_line}\n"

    # Update __all__ to include ws names
    if "__all__" in content:
        # Parse existing __all__ entries
        import re
        all_match = re.search(r"__all__\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if all_match:
            existing = set(re.findall(r'"(\w+)"', all_match.group(1)))
            all_names = sorted(existing | set(ws_class_names))
            new_all = "__all__ = [\n" + "".join(f'    "{n}",\n' for n in all_names) + "]"
            content = content[:all_match.start()] + new_all + content[all_match.end():]

    init_path.write_text(content + "\n" if not content.endswith("\n") else content)


def main() -> None:
    spec = fetch_spec()
    schemas = spec.get("components", {}).get("schemas", {})
    channels = spec.get("channels", {})

    ws_content = generate_ws_models(schemas, channels)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "ws.py").write_text(ws_content)

    # Collect class names for __init__.py
    class_names = ["Channel"]
    for name in schemas:
        if name in TYPE_ALIASES:
            continue
        if schemas[name].get("type") != "object":
            continue
        class_name = to_class_name(name)
        class_names.append(class_name)
        # Also add Msg class if it has inline msg
        msg_prop = schemas[name].get("properties", {}).get("msg", {})
        if msg_prop.get("type") == "object" and msg_prop.get("properties"):
            class_names.append(class_name.replace("Payload", "Msg"))

    print(f"  Wrote ws.py ({len(class_names)} classes, including Channel enum)")

    update_init(class_names)
    print("  Updated __init__.py")

    print(f"\nDone! Generated WS models in {OUTPUT_DIR / 'ws.py'}")


if __name__ == "__main__":
    main()
