#!/usr/bin/env python3
"""Sync API function docstrings from the Kalshi OpenAPI spec.

Usage:
    uv run python tools/sync_docstrings.py

Fetches https://docs.kalshi.com/openapi.yaml, matches each endpoint to
existing async functions in src/pykalshi/api/, and updates their docstrings
with the spec's summary and description.
"""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path
from typing import Any

import httpx
import yaml

SPEC_URL = "https://docs.kalshi.com/openapi.yaml"
API_DIR = Path(__file__).resolve().parent.parent / "src" / "pykalshi" / "api"


def fetch_spec() -> dict[str, Any]:
    print(f"Fetching {SPEC_URL}...")
    resp = httpx.get(SPEC_URL, timeout=15.0)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def build_endpoint_map(spec: dict[str, Any]) -> dict[tuple[str, str], dict[str, str]]:
    """Build (METHOD, path) -> {summary, description} map."""
    paths = spec.get("paths", {})
    result: dict[tuple[str, str], dict[str, str]] = {}

    for path_key, methods in paths.items():
        full_path = f"/trade-api/v2{path_key}" if not path_key.startswith("/trade-api") else path_key
        for method, details in methods.items():
            if method.upper() not in ("GET", "POST", "PUT", "DELETE"):
                continue
            summary = details.get("summary", "").strip()
            description = details.get("description", "").strip()
            result[(method.upper(), full_path)] = {
                "summary": summary,
                "description": description,
            }

    return result


def match_docstring_to_endpoint(
    docstring: str, endpoint_map: dict[tuple[str, str], dict[str, str]]
) -> dict[str, str] | None:
    """Extract METHOD and path from existing docstring and match to spec."""
    line = docstring.strip().split("\n")[0].strip()
    parts = line.split(None, 1)
    if len(parts) < 2 or parts[0] not in ("GET", "POST", "PUT", "DELETE"):
        return None

    method, path = parts[0], parts[1]

    # Direct match
    if (method, path) in endpoint_map:
        return endpoint_map[(method, path)]

    # Try template matching (our paths have actual values, spec has {param})
    for (spec_method, spec_path), info in endpoint_map.items():
        if spec_method != method:
            continue
        pattern = re.sub(r"\{[^}]+\}", "[^/]+", spec_path)
        if re.fullmatch(pattern, path):
            return info

    return None


def build_new_docstring(method_path_line: str, info: dict[str, str], indent: str) -> str:
    """Build a new docstring from spec info."""
    summary = info["summary"]
    description = info["description"]

    # Clean up description: strip leading whitespace, limit to first paragraph
    if description:
        # Remove markdown headers and excessive formatting
        lines = description.strip().splitlines()
        # Take up to first blank line or markdown header for brevity
        clean_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("##") or stripped.startswith("```"):
                break
            if not stripped and clean_lines:
                break
            clean_lines.append(stripped)
        description = " ".join(clean_lines).strip()

    parts = [f"{summary}."] if summary else []
    parts.append("")
    parts.append(method_path_line)

    if description:
        parts.append("")
        # Wrap long descriptions
        wrapped = textwrap.fill(description, width=88)
        parts.append(wrapped)

    content = f"\n{indent}".join(parts)
    return f'{indent}"""{content}\n{indent}"""'


def process_file(
    filepath: Path, endpoint_map: dict[tuple[str, str], dict[str, str]]
) -> int:
    """Update docstrings in a single API module file. Returns count of updates."""
    source = filepath.read_text()
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)

    updates: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue

        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue

        info = match_docstring_to_endpoint(docstring, endpoint_map)
        if info is None:
            continue

        # Extract the METHOD path line from existing docstring
        first_line = docstring.strip().split("\n")[0].strip()

        # Find the docstring node (first statement of function body)
        doc_node = node.body[0]
        assert isinstance(doc_node, ast.Expr) and isinstance(doc_node.value, ast.Constant)

        # Determine indentation from the docstring line
        doc_line_idx = doc_node.lineno - 1  # 0-based
        original_line = lines[doc_line_idx]
        indent = " " * (len(original_line) - len(original_line.lstrip()))

        new_docstring = build_new_docstring(first_line, info, indent)

        # Find the end line of the existing docstring
        end_line_idx = doc_node.end_lineno - 1  # 0-based

        updates.append((doc_line_idx, end_line_idx, new_docstring))

    if not updates:
        return 0

    # Apply updates in reverse order to preserve line numbers
    for start, end, new_doc in reversed(updates):
        lines[start : end + 1] = [new_doc + "\n"]

    filepath.write_text("".join(lines))
    return len(updates)


def main() -> None:
    spec = fetch_spec()
    endpoint_map = build_endpoint_map(spec)
    print(f"  {len(endpoint_map)} endpoints in spec")

    total = 0
    for py_file in sorted(API_DIR.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        count = process_file(py_file, endpoint_map)
        if count:
            print(f"  {py_file.name}: updated {count} docstrings")
            total += count

    print(f"\nDone! Updated {total} docstrings.")


if __name__ == "__main__":
    main()
