# Build & Quality — Makefile Targets

The project uses `make` for common development tasks. All targets are defined in the repo root `Makefile`.

## Dependency sync
- `make prepare` — Sync all workspace deps and install git hooks (`prek`).
- `make prepare-build` — Sync for release builds (no workspace sources).

## Formatting
- `make format` — Format all packages (ruff for Python, npm for web).
- `make format-kimi-cli` — `ruff check --fix` + `ruff format` for Kimi CLI.

## Lint & type check
- `make check` — Run checks for all packages.
- `make check-kimi-cli` — Runs in order:
  1. `ruff check`
  2. `ruff format --check`
  3. `pyright`
  4. `ty check || true` (non-blocking)
- `make check-kosong` / `check-pykaos` / `check-kimi-sdk` / `check-web` — Same pattern per package.

## Tests
- `make test` — All Python test suites.
- `make test-kimi-cli` — `pytest tests -vv` + `pytest tests_e2e -vv`.
- `make ai-test` — Run the AI test suite via `tests_ai/scripts/run.py`.

## Builds
- `make build` — Build all Python packages for release.
- `make build-bin` — Build standalone PyInstaller executable (one-file).
- `make build-bin-onedir` — Build standalone PyInstaller executable (one-dir).
