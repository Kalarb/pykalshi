"""OpenAPI spec validation — fetch live spec and validate per-endpoint REST API coverage.

Fetches https://docs.kalshi.com/openapi.yaml and checks that every spec
endpoint has a corresponding method in pykalshi's api/ modules (matched via
docstring annotations like ``GET /trade-api/v2/markets``).

Run with: uv run pytest tests/test_openapi_validation.py -v -s
"""

import ast
import re
from pathlib import Path

import httpx
import pytest
import yaml

pytestmark = pytest.mark.integration

SKIPPED_PATH_PREFIXES = {
    "/trade-api/v2/portfolio/subaccounts",
    "/trade-api/v2/portfolio/summary",
    "/trade-api/v2/fcm",
}

# Endpoints in the spec that we intentionally do not implement.
# Each entry should have a comment explaining why.
KNOWN_MISSING: set[tuple[str, str]] = {
    # v2 (event-market) order endpoints — not yet implemented
    ("POST", "/trade-api/v2/portfolio/events/orders"),
    ("DELETE", "/trade-api/v2/portfolio/events/orders/{order_id}"),
    ("POST", "/trade-api/v2/portfolio/events/orders/{order_id}/amend"),
    ("POST", "/trade-api/v2/portfolio/events/orders/{order_id}/decrease"),
    ("POST", "/trade-api/v2/portfolio/events/orders/batched"),
    ("DELETE", "/trade-api/v2/portfolio/events/orders/batched"),
    # Multivariate event collections — not yet implemented
    ("GET", "/trade-api/v2/multivariate_event_collections"),
    ("GET", "/trade-api/v2/multivariate_event_collections/{collection_ticker}"),
    ("GET", "/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"),
    ("POST", "/trade-api/v2/multivariate_event_collections/{collection_ticker}"),
    ("PUT", "/trade-api/v2/multivariate_event_collections/{collection_ticker}/lookup"),
    # Batch market candlesticks — not yet implemented
    ("GET", "/trade-api/v2/markets/candlesticks"),
    # Quote confirmation — not yet implemented
    ("PUT", "/trade-api/v2/communications/quotes/{quote_id}/confirm"),
}

_ENDPOINT_RE = re.compile(
    r"^\s*(GET|POST|PUT|DELETE|PATCH)\s+(/trade-api/v2\S+)", re.MULTILINE
)
API_DIR = Path(__file__).parent.parent / "src" / "pykalshi" / "api"


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
                        # Normalize path parameters — spec uses {param}, docstrings may vary
                        path = re.sub(r"\{[^}]+\}", lambda m: m.group(0), path)
                        endpoints.add((method, path))
    return endpoints


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
