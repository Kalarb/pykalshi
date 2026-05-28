"""Generate docs/API_COVERAGE.md from test results and code introspection.

Usage:
    # Run unit tests with JSON report, then generate coverage doc
    uv run pytest tests/ --ignore=tests/test_integration.py \
        --ignore=tests/test_ws_integration.py \
        --ignore=tests/test_openapi_validation.py \
        --ignore=tests/test_asyncapi_validation.py \
        --json-report --json-report-file=test-results.json
    uv run python tools/generate_coverage_report.py
"""

from __future__ import annotations

import ast
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "pykalshi"
TESTS = ROOT / "tests"
OUTPUT = ROOT / "docs" / "API_COVERAGE.md"
TEST_RESULTS_FILE = ROOT / "test-results.json"

# ── Section separators from http_client.py ──────────────────────────────────

CATEGORY_ORDER = [
    "Exchange",
    "Account",
    "Orders",
    "Order Groups",
    "Portfolio",
    "Markets",
    "Events",
    "Series",
    "Search",
    "Historical",
    "API Keys",
    "Communications",
    "Live Data",
    "Milestones",
    "Structured Targets",
    "Incentive Programs",
    "Event Orders (V2)",
    "Multivariate Event Collections",
]

# Map category → api module filename (for docstring extraction)
CATEGORY_TO_MODULE: dict[str, str] = {
    "Exchange": "exchange",
    "Account": "account",
    "Orders": "orders",
    "Order Groups": "order_groups",
    "Portfolio": "portfolio",
    "Markets": "markets",
    "Events": "events",
    "Series": "series",
    "Search": "search",
    "Historical": "historical",
    "API Keys": "api_keys",
    "Communications": "communications",
    "Live Data": "live_data",
    "Milestones": "milestones",
    "Structured Targets": "structured_targets",
    "Incentive Programs": "incentive_programs",
    "Event Orders (V2)": "event_orders",
    "Multivariate Event Collections": "multivariate_collections",
}


def parse_http_client_methods() -> dict[str, list[str]]:
    """Extract public async method names grouped by category from http_client.py.

    Uses section comments (``# --- Category ---``) to determine grouping, and
    AST parsing to reliably find all async method defs (including multi-line signatures).
    """
    source = (SRC / "http_client.py").read_text()
    lines = source.splitlines()

    # Build line_number -> category mapping from section comments
    line_to_category: dict[int, str] = {}
    current_category: str | None = None
    for i, line in enumerate(lines, start=1):
        m = re.match(r"\s*# --- (.+?) ---", line)
        if m:
            cat = m.group(1)
            current_category = None if cat in ("Core request engine", "HTTP verbs") else cat
        if current_category is not None:
            line_to_category[i] = current_category

    # AST-parse to find all async methods on the KalshiHttpClient class
    tree = ast.parse(source)
    categories: dict[str, list[str]] = {cat: [] for cat in CATEGORY_ORDER}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "KalshiHttpClient":
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and not item.name.startswith("_"):
                    cat = line_to_category.get(item.lineno)
                    if cat and cat in categories:
                        categories[cat].append(item.name)
            break

    return categories


def parse_api_module_docstrings() -> dict[str, str]:
    """Extract HTTP method + path from api module function docstrings.

    Returns mapping: function_name -> "GET /trade-api/v2/..."
    """
    endpoints: dict[str, str] = {}
    api_dir = SRC / "api"

    for py_file in api_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and not node.name.startswith("_"):
                docstring = ast.get_docstring(node)
                if docstring:
                    for doc_line in docstring.splitlines():
                        stripped = doc_line.strip()
                        if re.match(r"^(GET|POST|PUT|DELETE|PATCH) /", stripped):
                            # Shorten the path for readability
                            short = stripped.replace("/trade-api/v2", "")
                            endpoints[node.name] = short
                            break

    return endpoints


def find_test_functions(test_file: Path) -> set[str]:
    """Extract test function names from a test file (supports top-level and class methods)."""
    if not test_file.exists():
        return set()
    tree = ast.parse(test_file.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                names.add(node.name)
    return names


def find_methods_called_in_tests(test_file: Path) -> set[str]:
    """Scan a test file for `client.<method_name>(` calls to find which methods are exercised."""
    if not test_file.exists():
        return set()
    source = test_file.read_text()
    return set(re.findall(r"client\.(\w+)\s*\(", source))


def load_test_results() -> dict[str, str]:
    """Load pytest-json-report results. Returns mapping: test_name -> 'passed'/'failed'/'skipped'."""
    if not TEST_RESULTS_FILE.exists():
        return {}

    data = json.loads(TEST_RESULTS_FILE.read_text())
    results: dict[str, str] = {}
    for test in data.get("tests", []):
        # nodeid format: "tests/test_http_client.py::TestExchange::test_get_exchange_status"
        nodeid = test.get("nodeid", "")
        # Extract just the test function name
        name = nodeid.rsplit("::", 1)[-1] if "::" in nodeid else nodeid
        outcome = test.get("outcome", "unknown")
        results[name] = outcome

    return results


def match_test_status(method_name: str, test_results: dict[str, str]) -> str:
    """Find the test result for a given method name."""
    test_name = f"test_{method_name}"
    if test_name in test_results:
        outcome = test_results[test_name]
        return {"passed": "Pass", "failed": "Fail", "skipped": "Skip"}.get(outcome, outcome)
    return "—"


def check_integration_test_exists(
    method_name: str,
    integration_tests: set[str],
    methods_called: set[str],
) -> str:
    """Check if an integration test exercises a method.

    Primary signal: the method is actually called in the test file (via ``client.<method>(``).
    Fallback: fuzzy test-name matching.
    """
    if method_name in methods_called:
        return "Exists"
    if f"test_{method_name}" in integration_tests:
        return "Exists"
    # Fuzzy: check if method name appears within any test name
    for test_name in integration_tests:
        test_body = test_name.removeprefix("test_")
        if method_name in test_body:
            return "Exists"
    return "—"


def get_ws_channels() -> list[tuple[str, str]]:
    """Extract WebSocket channel names and descriptions from Channel enum."""
    source = (SRC / "models" / "ws.py").read_text()
    channels: list[tuple[str, str]] = []

    in_enum = False
    for line in source.splitlines():
        if "class Channel(str, Enum):" in line:
            in_enum = True
            continue
        if in_enum:
            if line and not line[0].isspace() and "class " in line:
                break
            m = re.match(r'\s+\w+ = "(\w+)"', line)
            if m:
                channels.append((m.group(1), ""))

    return channels


def generate_report() -> str:
    """Generate the full markdown coverage report."""
    categories = parse_http_client_methods()
    endpoints = parse_api_module_docstrings()
    test_results = load_test_results()

    # Scan for integration test coverage (function names + actual method calls)
    rest_integration_tests = find_test_functions(TESTS / "test_integration.py")
    rest_integration_calls = find_methods_called_in_tests(TESTS / "test_integration.py")
    ws_integration_tests = find_test_functions(TESTS / "test_ws_integration.py")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines: list[str] = []
    lines.append("# API Coverage")
    lines.append("")
    lines.append(f"> Auto-generated by CI on {now}. Do not edit manually.")
    lines.append("")

    # ── Summary table ────────────────────────────────────────────────────
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Endpoints | Unit Tests | Integration Tests |")
    lines.append("|----------|:---------:|:----------:|:-----------------:|")

    total_endpoints = 0
    total_unit = 0
    total_integration = 0

    summary_rows: list[str] = []
    for cat in CATEGORY_ORDER:
        methods = categories.get(cat, [])
        n_endpoints = len(methods)
        n_unit = sum(1 for m in methods if match_test_status(m, test_results) != "—")
        n_integration = sum(
            1 for m in methods if check_integration_test_exists(m, rest_integration_tests, rest_integration_calls) != "—"
        )
        total_endpoints += n_endpoints
        total_unit += n_unit
        total_integration += n_integration
        summary_rows.append(f"| {cat} | {n_endpoints} | {n_unit}/{n_endpoints} | {n_integration}/{n_endpoints} |")

    lines.extend(summary_rows)
    lines.append(
        f"| **Total** | **{total_endpoints}** | **{total_unit}/{total_endpoints}** | **{total_integration}/{total_endpoints}** |"
    )
    lines.append("")

    # ── HTTP endpoint tables ─────────────────────────────────────────────
    lines.append("## HTTP Endpoints")
    lines.append("")

    for cat in CATEGORY_ORDER:
        methods = categories.get(cat, [])
        if not methods:
            continue

        lines.append(f"### {cat}")
        lines.append("")
        lines.append("| Method | Endpoint | Unit | Integration | Notes |")
        lines.append("|--------|----------|:----:|:-----------:|-------|")

        for method in methods:
            endpoint = endpoints.get(method, "—")
            unit = match_test_status(method, test_results)
            integration = check_integration_test_exists(method, rest_integration_tests, rest_integration_calls)
            lines.append(f"| `{method}` | `{endpoint}` | {unit} | {integration} | |")

        lines.append("")

    # ── WebSocket channels ───────────────────────────────────────────────
    ws_channels = get_ws_channels()
    if ws_channels:
        lines.append("## WebSocket Channels")
        lines.append("")
        lines.append("| Channel | Unit | Integration | Notes |")
        lines.append("|---------|:----:|:-----------:|-------|")

        ws_unit_tests = find_test_functions(TESTS / "test_ws_client.py")

        for channel_name, _ in ws_channels:
            # WS tests use patterns like test_subscribe_orderbook_delta, test_channel_orderbook_delta
            unit = "—"
            for test_name in test_results:
                if channel_name in test_name:
                    outcome = test_results[test_name]
                    unit = {"passed": "Pass", "failed": "Fail", "skipped": "Skip"}.get(
                        outcome, outcome
                    )
                    break
            else:
                # Check if test function exists even without results
                for t in ws_unit_tests:
                    if channel_name in t:
                        unit = "Exists"
                        break

            integration = "—"
            for t in ws_integration_tests:
                if channel_name in t:
                    integration = "Exists"
                    break

            lines.append(f"| `{channel_name}` | {unit} | {integration} | |")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    report = generate_report()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report)
    print(f"Coverage report written to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
