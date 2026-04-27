#!/usr/bin/env python3
"""Generate Pydantic v2 models from the Kalshi OpenAPI spec.

Usage:
    uv run python tools/generate_models.py

Fetches https://docs.kalshi.com/openapi.yaml, parses all component schemas,
and writes typed models to src/pykalshi/models/.
"""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path
from typing import Any

import httpx
import yaml

SPEC_URL = "https://docs.kalshi.com/openapi.yaml"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "src" / "pykalshi" / "models"

# Schemas to skip (subaccounts, FCM, etc.)
SKIP_PREFIXES = ("Subaccount", "IntraExchange", "Fcm")

# Type alias schemas that map to simple Python types (not full Pydantic models)
TYPE_ALIASES = {
    "FixedPointDollars": "str",
    "FixedPointCount": "str",
}

# Fields the OpenAPI spec marks as required but the real API returns null for.
# Keyed by (schema_name, field_name). Forces the field to be nullable with a
# None default, regardless of what the spec says. Verified against production
# responses — the spec is simply wrong for these fields.
NULLABLE_OVERRIDES: set[tuple[str, str]] = {
    ("Series", "tags"),
    ("Series", "settlement_sources"),
    ("Series", "contract_url"),
    ("Series", "contract_terms_url"),
    ("Series", "additional_prohibitions"),
    ("GetOrderQueuePositionsResponse", "queue_positions"),
    ("GetLiveDatasResponse", "live_datas"),
}


def fetch_spec() -> dict[str, Any]:
    """Fetch the OpenAPI spec from Kalshi docs."""
    print(f"Fetching {SPEC_URL}...")
    resp = httpx.get(SPEC_URL, timeout=15.0)
    resp.raise_for_status()
    spec = yaml.safe_load(resp.text)
    print(f"  Loaded {len(spec.get('components', {}).get('schemas', {}))} schemas")
    return spec


def should_skip(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in SKIP_PREFIXES)


def ref_to_name(ref: str) -> str:
    """Extract schema name from $ref string."""
    return ref.rsplit("/", 1)[-1]


def resolve_type(
    prop: dict[str, Any], required: bool, included_names: set[str] | None = None
) -> str:
    """Convert an OpenAPI property schema to a Python type annotation."""
    nullable = prop.get("nullable", False)

    # Handle allOf wrapper (common for nullable refs)
    if "allOf" in prop and len(prop["allOf"]) == 1:
        inner = {**prop["allOf"][0], **{k: v for k, v in prop.items() if k != "allOf"}}
        return resolve_type(inner, required, included_names)

    if "$ref" in prop:
        ref_name = ref_to_name(prop["$ref"])
        if ref_name in TYPE_ALIASES:
            py_type = TYPE_ALIASES[ref_name]
        elif included_names is not None and ref_name not in included_names:
            py_type = "Any"
        else:
            py_type = ref_name
    elif prop.get("type") == "string":
        if "enum" in prop:
            py_type = "str"
        elif prop.get("format") == "date-time":
            py_type = "str"
        else:
            py_type = "str"
    elif prop.get("type") == "integer":
        py_type = "int"
    elif prop.get("type") == "number":
        py_type = "float"
    elif prop.get("type") == "boolean":
        py_type = "bool"
    elif prop.get("type") == "array":
        items = prop.get("items", {})
        item_type = resolve_type(items, required=True, included_names=included_names)
        py_type = f"list[{item_type}]"
    elif prop.get("type") == "object":
        additional = prop.get("additionalProperties")
        if isinstance(additional, dict):
            val_type = resolve_type(additional, required=True, included_names=included_names)
            py_type = f"dict[str, {val_type}]"
        elif additional is True:
            py_type = "dict[str, Any]"
        else:
            py_type = "dict[str, Any]"
    else:
        py_type = "Any"

    if nullable or not required:
        return f"{py_type} | None"
    return py_type


def resolve_default(py_type: str, required: bool) -> str:
    """Return default value string for a field."""
    if required and "| None" not in py_type:
        return ""
    return " = None"


def generate_enum(name: str, schema: dict[str, Any]) -> str:
    """Generate a StrEnum class."""
    values = schema.get("enum", [])
    lines = [f"class {name}(str, Enum):"]
    desc = schema.get("description")
    if desc:
        lines.append(f'    """{desc}"""')
    lines.append("")
    for val in values:
        member_name = val.upper().replace("-", "_").replace(" ", "_")
        lines.append(f'    {member_name} = "{val}"')
    return "\n".join(lines)


def generate_model(
    name: str,
    schema: dict[str, Any],
    all_schemas: dict[str, Any],
    included_names: set[str] | None = None,
) -> str:
    """Generate a Pydantic BaseModel class."""
    properties = schema.get("properties", {})
    required_set = set(schema.get("required", []))

    lines = [f"class {name}(BaseModel):"]
    desc = schema.get("description")
    if desc:
        lines.append(f'    """{desc}"""')
        lines.append("")
    lines.append('    model_config = ConfigDict(extra="ignore", populate_by_name=True)')
    lines.append("")

    if not properties:
        lines.append("    pass")
        return "\n".join(lines)

    for prop_name, prop_schema in properties.items():
        is_required = prop_name in required_set
        is_deprecated = prop_schema.get("deprecated", False)

        # Force nullable for fields the spec gets wrong
        force_nullable = (name, prop_name) in NULLABLE_OVERRIDES
        effective_required = is_required and not force_nullable
        py_type = resolve_type(prop_schema, required=effective_required, included_names=included_names)
        default = resolve_default(py_type, effective_required)
        description = prop_schema.get("description", "").strip()

        # Escape quotes in descriptions
        if description:
            description = description.replace("\\", "\\\\").replace('"', '\\"')

        # Handle reserved words
        field_name = prop_name
        is_alias = prop_name in ("type", "class")
        if prop_name == "type":
            field_name = "type_"
        elif prop_name == "class":
            field_name = "class_"

        # Build Field() kwargs
        if is_alias or description or is_deprecated:
            default_val = default.strip(" =") or "..."
            field_kwargs = [default_val]
            if is_alias:
                field_kwargs.append(f'alias="{prop_name}"')
            if description:
                field_kwargs.append(f'description="{description}"')
            if is_deprecated:
                field_kwargs.append("deprecated=True")
            lines.append(f"    {field_name}: {py_type} = Field({', '.join(field_kwargs)})")
        else:
            lines.append(f"    {field_name}: {py_type}{default}")

    return "\n".join(lines)


def collect_refs(schema: dict[str, Any]) -> set[str]:
    """Recursively collect all $ref names used by a schema."""
    refs: set[str] = set()
    if "$ref" in schema:
        refs.add(ref_to_name(schema["$ref"]))
    for value in schema.values():
        if isinstance(value, dict):
            refs |= collect_refs(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    refs |= collect_refs(item)
    return refs


def categorize_schemas(
    schemas: dict[str, Any],
) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    """Split schemas into enums, core, requests, responses."""
    enums: dict[str, Any] = {}
    requests: dict[str, Any] = {}
    responses: dict[str, Any] = {}
    core: dict[str, Any] = {}

    for name, schema in schemas.items():
        if should_skip(name):
            continue
        if name in TYPE_ALIASES:
            continue
        if schema.get("type") == "string" and "enum" in schema:
            enums[name] = schema
        elif name.endswith("Request"):
            requests[name] = schema
        elif name.endswith("Response"):
            responses[name] = schema
        else:
            core[name] = schema

    return enums, core, requests, responses


def collect_imports(
    schemas: dict[str, Any], all_schemas: dict[str, Any], included: set[str]
) -> set[str]:
    """Collect which model names are referenced by a set of schemas."""
    refs: set[str] = set()
    for schema in schemas.values():
        refs |= collect_refs(schema)
    # Filter to names that exist in the included set
    return {r for r in refs if r in included and r not in TYPE_ALIASES}


def topological_sort(
    schemas: dict[str, Any], all_schemas: dict[str, Any]
) -> list[str]:
    """Sort schema names so dependencies come first."""
    # Build dependency graph within the given schemas
    names = set(schemas.keys())
    deps: dict[str, set[str]] = {}
    for name, schema in schemas.items():
        refs = collect_refs(schema)
        deps[name] = {r for r in refs if r in names and r != name}

    sorted_names: list[str] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visited:
            return
        if name in visiting:
            # Circular dependency — break it
            return
        visiting.add(name)
        for dep in deps.get(name, set()):
            visit(dep)
        visiting.discard(name)
        visited.add(name)
        sorted_names.append(name)

    for name in schemas:
        visit(name)

    return sorted_names


def write_enums(enums: dict[str, Any]) -> str:
    """Generate enums.py content."""
    lines = [
        '"""Enum types generated from the Kalshi OpenAPI spec."""',
        "",
        "# NOTE: Auto-generated by tools/generate_models.py — do not edit manually.",
        "",
        "from __future__ import annotations",
        "",
        "from enum import Enum",
        "",
        "",
    ]

    for name in sorted(enums):
        lines.append(generate_enum(name, enums[name]))
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_models(
    filename_label: str,
    schemas: dict[str, Any],
    all_schemas: dict[str, Any],
    included_names: set[str],
    extra_imports: list[str] | None = None,
) -> str:
    """Generate a models file with proper imports and ordering."""
    sorted_names = topological_sort(schemas, all_schemas)

    # Determine cross-file imports needed
    refs_in_schemas = collect_imports(schemas, all_schemas, included_names)
    external_refs = refs_in_schemas - set(schemas.keys())

    # Figure out which files the external refs come from
    enum_names: set[str] = set()
    core_names: set[str] = set()
    for ref in external_refs:
        ref_schema = all_schemas.get(ref, {})
        if ref_schema.get("type") == "string" and "enum" in ref_schema:
            enum_names.add(ref)
        elif not ref.endswith("Request") and not ref.endswith("Response"):
            core_names.add(ref)

    # Check if Any is needed by generating all types and checking
    needs_any = False
    for schema in schemas.values():
        for prop in schema.get("properties", {}).values():
            resolved = resolve_type(prop, required=True, included_names=included_names)
            if "Any" in resolved:
                needs_any = True
                break
        if needs_any:
            break

    lines = [
        f'"""{filename_label} generated from the Kalshi OpenAPI spec."""',
        "",
        "# NOTE: Auto-generated by tools/generate_models.py — do not edit manually.",
        "",
        "from __future__ import annotations",
        "",
    ]

    typing_imports = []
    if needs_any:
        typing_imports.append("Any")
    if typing_imports:
        lines.append(f"from typing import {', '.join(sorted(typing_imports))}")
        lines.append("")

    # Check if any model uses Field (aliases or descriptions)
    needs_field = False
    for schema in schemas.values():
        for prop_name, prop in schema.get("properties", {}).items():
            if prop_name in ("type", "class") or prop.get("description") or prop.get("deprecated"):
                needs_field = True
                break
        if needs_field:
            break

    pydantic_imports = ["BaseModel", "ConfigDict"]
    if needs_field:
        pydantic_imports.append("Field")
    lines.append(f"from pydantic import {', '.join(pydantic_imports)}")
    lines.append("")

    if extra_imports:
        for imp in extra_imports:
            lines.append(imp)
        lines.append("")

    if enum_names:
        names_str = ", ".join(sorted(enum_names))
        lines.append(f"from .enums import {names_str}")
    if core_names and filename_label != "Core domain models":
        names_str = ", ".join(sorted(core_names))
        lines.append(f"from .core import {names_str}")
    if enum_names or (core_names and filename_label != "Core domain models"):
        lines.append("")

    lines.append("")

    for name in sorted_names:
        schema = schemas[name]
        if schema.get("type") == "array":
            # Array-type schema — generate as type alias
            items = schema.get("items", {})
            item_type = resolve_type(items, required=True)
            lines.append(f"{name} = list[{item_type}]")
        elif schema.get("type") in ("string", "integer", "number", "boolean"):
            # Simple type alias
            py_type = {"string": "str", "integer": "int", "number": "float", "boolean": "bool"}
            lines.append(f"{name} = {py_type[schema['type']]}")
        else:
            lines.append(generate_model(name, schema, all_schemas, included_names))
        lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_init(
    enums: dict[str, Any],
    core: dict[str, Any],
    requests: dict[str, Any],
    responses: dict[str, Any],
) -> str:
    """Generate models/__init__.py with all exports."""
    lines = [
        '"""Typed models for the Kalshi API."""',
        "",
        "# NOTE: Auto-generated by tools/generate_models.py — do not edit manually.",
        "",
    ]

    all_names: list[str] = []

    if enums:
        names = sorted(enums.keys())
        all_names.extend(names)
        lines.append(f"from .enums import {', '.join(names)}")
    if core:
        names = sorted(core.keys())
        all_names.extend(names)
        lines.append(f"from .core import {', '.join(names)}")
    if requests:
        names = sorted(requests.keys())
        all_names.extend(names)
        lines.append(f"from .requests import {', '.join(names)}")
    if responses:
        names = sorted(responses.keys())
        all_names.extend(names)
        lines.append(f"from .responses import {', '.join(names)}")

    lines.append("")
    lines.append("__all__ = [")
    for name in sorted(all_names):
        lines.append(f'    "{name}",')
    lines.append("]")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    spec = fetch_spec()
    all_schemas = spec.get("components", {}).get("schemas", {})

    enums, core, requests, responses = categorize_schemas(all_schemas)

    print(f"  Enums: {len(enums)}, Core: {len(core)}, Requests: {len(requests)}, Responses: {len(responses)}")
    skipped = sum(1 for name in all_schemas if should_skip(name) or name in TYPE_ALIASES)
    print(f"  Skipped: {skipped}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # All non-skipped, non-alias names
    included_names = set(enums) | set(core) | set(requests) | set(responses)

    # Write enums
    enums_content = write_enums(enums)
    (OUTPUT_DIR / "enums.py").write_text(enums_content)
    print(f"  Wrote enums.py ({len(enums)} enums)")

    # Write core models
    core_content = write_models("Core domain models", core, all_schemas, included_names)
    (OUTPUT_DIR / "core.py").write_text(core_content)
    print(f"  Wrote core.py ({len(core)} models)")

    # Write request models
    requests_content = write_models("Request models", requests, all_schemas, included_names)
    (OUTPUT_DIR / "requests.py").write_text(requests_content)
    print(f"  Wrote requests.py ({len(requests)} models)")

    # Write response models
    responses_content = write_models("Response models", responses, all_schemas, included_names)
    (OUTPUT_DIR / "responses.py").write_text(responses_content)
    print(f"  Wrote responses.py ({len(responses)} models)")

    # Write __init__.py
    init_content = write_init(enums, core, requests, responses)
    (OUTPUT_DIR / "__init__.py").write_text(init_content)
    print(f"  Wrote __init__.py")

    print("\nDone! Generated models in", OUTPUT_DIR)


if __name__ == "__main__":
    main()
