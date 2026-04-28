# Contributing

## Branch Workflow

- All changes go through a pull request against `main` — no direct pushes
- PRs are **squash merged** (repo enforced), so the PR title becomes the commit message
- Required checks must pass before merging: `lint`, `rest-unit-tests`, `ws-unit-tests`

## PR Title Format

PR titles **must** follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(optional-scope): description
```

The PR title drives automatic version bumping on merge:

| Type | Version Bump | Example |
|---|---|---|
| `feat` | **minor** (0.1.x → 0.2.0) | `feat: add batch order amendment` |
| `fix` | **patch** (0.1.1 → 0.1.2) | `fix: handle nullable fields in responses` |
| `refactor` | **patch** | `refactor: extract rate limiter into separate module` |
| `perf` | **patch** | `perf: use orjson for message parsing` |
| `docs` | no bump | `docs: update API coverage tables` |
| `ci` | no bump | `ci: add OpenAPI validation workflow` |
| `test` | no bump | `test: add resubscribe_channel integration test` |
| `chore` | no bump | `chore: update dependencies` |
| `style` | no bump | `style: fix ruff formatting` |

## Breaking Changes

Breaking changes trigger a **major** version bump. Signal them in one of two ways:

1. Add `!` after the type in the PR title:
   ```
   feat!: remove deprecated get_live_data_legacy
   ```

2. Include `BREAKING CHANGE:` in the PR description body:
   ```
   BREAKING CHANGE: get_live_data_legacy has been removed. Use get_live_data instead.
   ```

## Running Tests Locally

```bash
# Unit tests
uv run pytest tests/test_http_client.py tests/test_auth.py tests/test_rate_limiter.py -v
uv run pytest tests/test_ws_client.py -v

# Lint
uv run ruff check src/ tests/

# Integration tests (requires credentials in .env)
uv run pytest tests/test_integration.py -v        # REST — DEMO API
uv run pytest tests/test_ws_integration.py -v      # WebSocket — PROD API (read-only)

# Spec validation
uv run pytest tests/test_openapi_validation.py -v
uv run pytest tests/test_asyncapi_validation.py -v
```

## Code Generation

Models in `src/pykalshi/models/` are **auto-generated** from the Kalshi OpenAPI and AsyncAPI specs. Do not edit them manually. Instead:

```bash
uv run python tools/generate_models.py       # HTTP models
uv run python tools/generate_ws_models.py    # WebSocket models
uv run python tools/sync_docstrings.py       # API function docstrings
```
