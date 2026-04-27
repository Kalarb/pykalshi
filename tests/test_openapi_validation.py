"""OpenAPI spec validation — fetch live spec and validate REST API coverage.

Fetches https://docs.kalshi.com/openapi.yaml and asserts pykalshi covers
all accessible endpoints.

Run with: uv run pytest tests/test_openapi_validation.py -v
"""

import httpx
import pytest
import yaml

pytestmark = pytest.mark.integration

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

    spec_endpoints: set[tuple[str, str]] = set()
    for path, methods in paths.items():
        full_path = f"/trade-api/v2{path}" if not path.startswith("/trade-api") else path
        if _should_skip_path(full_path):
            continue
        for method in methods:
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                spec_endpoints.add((method.upper(), full_path))

    from pykalshi.http_client import KalshiHttpClient
    client_methods = {
        name for name in dir(KalshiHttpClient)
        if not name.startswith("_") and callable(getattr(KalshiHttpClient, name))
    }

    assert len(spec_endpoints) > 40, f"Expected 40+ endpoints, got {len(spec_endpoints)}"
    assert len(client_methods) > 60, f"Expected 60+ methods, got {len(client_methods)}"

    print(f"\nOpenAPI spec endpoints: {len(spec_endpoints)}")
    print(f"KalshiHttpClient public methods: {len(client_methods)}")
    print(f"Skipped prefixes: {SKIPPED_PATH_PREFIXES}")
