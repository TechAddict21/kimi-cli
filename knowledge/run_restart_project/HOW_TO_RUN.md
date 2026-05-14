# How to Run / Restart the Project

This is a **uv workspace** monorepo. Use `uv run ...` for everything — no manual venv activation needed.

## Initial Setup

```bash
# Sync all workspace deps + install git hooks
make prepare

# Or just sync without hooks
uv sync --frozen --all-extras --all-packages
```

## Run the CLI

```bash
# Interactive shell mode
uv run pc-kimi

# With a specific work directory
uv run pc-kimi /path/to/project

# Print mode (non-interactive)
uv run pc-kimi --print "your prompt here"

# With a specific agent spec
uv run pc-kimi --agent custom-agent
```

The CLI script name is **`pc-kimi`** / `pc-kimi-cli` (defined in `pyproject.toml`).

## Tests

```bash
# All tests
make test

# Just Kimi CLI tests
uv run pytest tests -vv
uv run pytest tests_e2e -vv

# Just hooks tests
uv run pytest tests/hooks -vv

# Kosong tests
uv run --project packages/kosong --directory packages/kosong pytest --doctest-modules -vv

# Pykaos tests
uv run --project packages/kaos --directory packages/kaos pytest tests -vv

# Kimi-sdk tests
uv run --project sdks/kimi-sdk --directory sdks/kimi-sdk pytest tests -vv
```

## Lint / Format / Type Check

```bash
# Auto-format everything
make format

# Check everything (ruff + pyright)
make check

# Per-package targets
make format-kimi-cli    # or format-kosong, format-pykaos
make check-kimi-cli     # or check-kosong, check-pykaos

# Individual tools
uv run ruff check
uv run ruff format
uv run pyright
uv run ty check
```

### Pre-commit Hooks

`make prepare` installs pre-commit hooks. On `git commit`, hooks run per modified package:
- Root (`kimi-cli`): `make format-kimi-cli` + `make check-kimi-cli`
- `packages/kosong`: `make format-kosong` + `make check-kosong`
- `packages/kaos`: `make format-pykaos` + `make check-pykaos`

A hook fails if `ruff check`, `ruff format --check`, or `pyright` reports errors. `ty check` runs but is non-blocking (`|| true`).

## Web / Vis Dev Servers

```bash
# Web backend (port 5494)
make web-back

# Web frontend
make web-front

# Vis backend (port 5495)
make vis-back

# Vis frontend
make vis-front
```

## Build

```bash
# Build Python wheels/sdists for all workspace packages
make build

# Build standalone binary with PyInstaller
make build-bin

# Build just one package
uv build --package kosong --no-sources --out-dir dist/kosong
```

## Quick Reference (Makefile)

| Command | What it does |
|---------|-------------|
| `make prepare` | Sync deps + install git hooks |
| `make format` | Auto-format all code |
| `make check` | Run lint + type checks |
| `make test` | Run all test suites |
| `make build` | Build all packages |
| `make build-bin` | Build standalone executable |
| `make ai-test` | Run AI test suite |
