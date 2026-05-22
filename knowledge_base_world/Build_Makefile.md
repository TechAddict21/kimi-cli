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

## Pre-commit hooks
- `make install-prek` — Install the `prek` uv tool and register git hooks.
- `make prepare` — Runs `install-prek` as part of dependency sync.
- Root hook config (`.pre-commit-config.yaml`) runs `make format-kimi-cli` and `make check-kimi-cli`.
- Per-package hook configs (`packages/kaos/.pre-commit-config.yaml`, `packages/kosong/.pre-commit-config.yaml`) use `orphan: true` and run `make -C ../.. format-<pkg>` / `check-<pkg>`.
- **Failure behavior**: If any package's `check-*` target fails (e.g., `ruff check` finds E501 line-too-long), the commit is blocked. All packages' hooks run independently.

## Ruff configuration
- Line length: **100 characters** (E501).
- `make check-kimi-cli` runs `ruff check` then `ruff format --check`.
- `make format-kimi-cli` runs `ruff check --fix` then `ruff format`.

### Fixing E501 line-too-long errors
`ruff check --fix` auto-fixes many issues, but E501 often requires manual edits when a line cannot be broken automatically:

- **Long comments**: split the comment across two lines.
  ```python
  # Short messages (≤2 words, no technical chars) can't match KB entries
  # — skip the LLM call
  ```
- **Long boolean expressions**: wrap the entire expression with parentheses to enable implicit line continuation.
  ```python
  _streamed_live = (
      self._reviewer_enabled and bool(self._runtime.config.reviewer_model)
  )
  ```
- **Long strings or f-strings**: split into multiple parts or use parentheses.

After manual fixes, run `make format-kimi-cli` to re-format and `make check-kimi-cli` to verify.

## Builds
- `make build` — Build all Python packages for release.
- `make build-bin` — Build standalone PyInstaller executable (one-file).
- `make build-bin-onedir` — Build standalone PyInstaller executable (one-dir).
