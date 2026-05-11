"""OpenAPI spec validation — fetch live spec and validate REST API coverage + schema drift.

Fetches https://docs.kalshi.com/openapi.yaml and checks:
1. Every spec endpoint has a corresponding method in pykalshi's api/ modules
2. Every spec schema has a corresponding Pydantic model with matching fields/enums

Run with: uv run pytest tests/test_openapi_validation.py -v -s
"""

import ast
import re
from pathlib import Path

import httpx
import pytest
import yaml

import pykalshi.models as models

pytestmark = pytest.mark.integration

SKIPPED_PATH_PREFIXES = {
    "/trade-api/v2/portfolio/subaccounts",
    "/trade-api/v2/portfolio/summary",
    "/trade-api/v2/fcm",
}

# Endpoints in the spec that we intentionally do not implement.
# Empty — we want the test to fail on any missing endpoint so gaps are visible.
KNOWN_MISSING: set[tuple[str, str]] = set()

_ENDPOINT_RE = re.compile(
    r"^\s*(GET|POST|PUT|DELETE|PATCH)\s+(/trade-api/v2\S+)", re.MULTILINE
)
API_DIR = Path(__file__).parent.parent / "src" / "pykalshi" / "api"

# Matches generate_models.py SKIP_PREFIXES and TYPE_ALIASES
_SKIP_PREFIXES = ("Subaccount", "IntraExchange", "Fcm")
_TYPE_ALIASES = {"FixedPointDollars", "FixedPointCount"}
_RESERVED_WORDS = {"type": "type_", "class": "class_"}


def _parse_spec_endpoints(spec: dict) -> set[tuple[str, str]]:
    """Extract (METHOD, PATH) pairs from an OpenAPI spec."""
    endpoints: set[tuple[str, str]] = set()
    for path, methods in spec.get("paths", {}).items():
        full_path = f"/trade-api/v2{path}" if not path.startswith("/trade-api") else path
        if any(full_path.startswith(prefix) for prefix in SKIPPED_PATH_PREFIXES):
            continue
        for method in methods:
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                endpoints.add((method.upper(), full_path))
    return endpoints


def _parse_pykalshi_endpoints() -> set[tuple[str, str]]:
    """Extract (METHOD, PATH) from docstrings in src/pykalshi/api/*.py."""
    endpoints: set[tuple[str, str]] = set()
    for py_file in sorted(API_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        source = py_file.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node)
                if docstring:
                    match = _ENDPOINT_RE.search(docstring)
                    if match:
                        method = match.group(1).upper()
                        path = match.group(2)
                        path = re.sub(r"\{[^}]+\}", lambda m: m.group(0), path)
                        endpoints.add((method, path))
    return endpoints


def _resolve_properties(schema: dict, all_schemas: dict) -> dict:
    """Resolve a schema's properties, handling allOf wrappers."""
    if "allOf" in schema:
        merged: dict = {}
        for sub in schema["allOf"]:
            if "$ref" in sub:
                ref_name = sub["$ref"].rsplit("/", 1)[-1]
                ref_schema = all_schemas.get(ref_name, {})
                merged.update(ref_schema.get("properties", {}))
            else:
                merged.update(sub.get("properties", {}))
        merged.update(schema.get("properties", {}))
        return merged
    return schema.get("properties", {})


def _spec_field_to_model_field(field_name: str) -> str:
    """Map spec property name to Python model field name."""
    return _RESERVED_WORDS.get(field_name, field_name)


def _get_model_class(name: str) -> type | None:
    """Look up a Pydantic model class by name from pykalshi.models."""
    return getattr(models, name, None)


@pytest.mark.asyncio
async def test_openapi_coverage() -> None:
    """Every spec endpoint should be implemented in pykalshi or listed in KNOWN_MISSING."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://docs.kalshi.com/openapi.yaml", timeout=15.0)
        resp.raise_for_status()

    spec = yaml.safe_load(resp.text)
    spec_endpoints = _parse_spec_endpoints(spec)
    our_endpoints = _parse_pykalshi_endpoints()

    missing = spec_endpoints - our_endpoints - KNOWN_MISSING
    extra = our_endpoints - spec_endpoints

    print(f"\nOpenAPI spec endpoints: {len(spec_endpoints)}")
    print(f"pykalshi endpoints: {len(our_endpoints)}")
    print(f"Skipped prefixes: {SKIPPED_PATH_PREFIXES}")

    if KNOWN_MISSING & spec_endpoints:
        print(f"\nKnown missing ({len(KNOWN_MISSING & spec_endpoints)}):")
        for method, path in sorted(KNOWN_MISSING & spec_endpoints):
            print(f"  {method} {path}")

    if extra:
        print(f"\npykalshi-only (not in spec, {len(extra)}):")
        for method, path in sorted(extra):
            print(f"  {method} {path}")

    if missing:
        print(f"\nNEW MISSING (not in KNOWN_MISSING, {len(missing)}):")
        for method, path in sorted(missing):
            print(f"  {method} {path}")

    assert missing == set(), (
        "Spec endpoints not implemented and not in KNOWN_MISSING:\n"
        + "\n".join(f"  {m} {p}" for m, p in sorted(missing))
    )


@pytest.mark.asyncio
async def test_openapi_schema_coverage() -> None:
    """Every spec schema should have a matching Pydantic model with all fields and enum values."""
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://docs.kalshi.com/openapi.yaml", timeout=15.0)
        resp.raise_for_status()

    spec = yaml.safe_load(resp.text)
    schemas = spec.get("components", {}).get("schemas", {})

    missing_models: list[str] = []
    missing_fields: list[str] = []
    missing_enum_values: list[str] = []

    for schema_name, schema in sorted(schemas.items()):
        if any(schema_name.startswith(p) for p in _SKIP_PREFIXES):
            continue
        if schema_name in _TYPE_ALIASES:
            continue

        model_cls = _get_model_class(schema_name)

        # --- Enum schemas ---
        if schema.get("type") == "string" and "enum" in schema:
            if model_cls is None:
                missing_models.append(schema_name)
                continue
            spec_values = set(schema["enum"])
            model_values = {m.value for m in model_cls}
            for val in sorted(spec_values - model_values):
                missing_enum_values.append(f"{schema_name}.{val}")
            continue

        # --- Object schemas ---
        if model_cls is None:
            missing_models.append(schema_name)
            continue

        spec_props = _resolve_properties(schema, schemas)
        if not spec_props:
            continue

        model_fields = set(model_cls.model_fields.keys()) if hasattr(model_cls, "model_fields") else set()

        for prop_name in spec_props:
            expected_field = _spec_field_to_model_field(prop_name)
            if expected_field not in model_fields:
                missing_fields.append(f"{schema_name}.{prop_name}")

    # --- Report ---
    print(f"\nOpenAPI schemas checked: {len(schemas)}")

    if missing_models:
        print(f"\nMissing models ({len(missing_models)}):")
        for name in missing_models:
            print(f"  {name}")

    if missing_fields:
        print(f"\nMissing fields ({len(missing_fields)}):")
        for entry in missing_fields:
            print(f"  {entry}")

    if missing_enum_values:
        print(f"\nMissing enum values ({len(missing_enum_values)}):")
        for entry in missing_enum_values:
            print(f"  {entry}")

    all_gaps = missing_models + missing_fields + missing_enum_values
    assert all_gaps == [], (
        "Schema drift detected:\n" + "\n".join(f"  {g}" for g in all_gaps)
    )
