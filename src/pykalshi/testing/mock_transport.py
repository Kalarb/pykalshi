"""Mock transport factory for testing."""

from __future__ import annotations

from typing import Any

import httpx


def make_mock_transport(
    routes: dict[tuple[str, str], Any] | None = None,
    default_status: int = 200,
) -> httpx.MockTransport:
    """Build an httpx MockTransport with canned responses.

    Args:
        routes: Mapping of (METHOD, path_prefix) -> response body.
                If value is an int, it becomes the status code with empty body.
        default_status: Status code for matched routes (default 200).

    Example:
        transport = make_mock_transport({
            ("GET", "/trade-api/v2/exchange/status"): {"exchange_active": True},
            ("POST", "/trade-api/v2/portfolio/orders"): {"order": {"id": "abc"}},
        })
    """
    route_map = routes or {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method.upper()

        for (route_method, route_path), body in route_map.items():
            if method == route_method.upper() and path.startswith(route_path):
                if isinstance(body, int):
                    return httpx.Response(body)
                return httpx.Response(
                    default_status,
                    json=body,
                )

        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler)
