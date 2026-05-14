# Common Lint / Type Errors and Fixes

## Ruff Errors

### E501 — Line too long
- **Rule**: Max line length is **100 characters**.
- **Fix**: Break the line using parentheses or implicit continuation.

```python
# Bad
logger.info("Reviewer enabled (max_iterations={max})", max=self._runtime.config.reviewer_max_iterations)

# Good
logger.info(
    "Reviewer enabled (max_iterations={max})",
    max=self._runtime.config.reviewer_max_iterations,
)
```

### F841 — Local variable assigned but never used
- **Fix**: Remove the assignment if the variable is not needed.

```python
# Bad
eof_mark = shell.mark()
shell.send_key("ctrl_d")

# Good
shell.send_key("ctrl_d")
```

## Pyright Errors

### `reportUnknownMemberType` / `reportUnknownArgumentType` — Empty list inference
When a list is initialized empty without a type annotation, pyright infers `list[Unknown]`. Subsequent `append`/`extend` calls fail.

```python
# Bad
banner_lines = []
banner_lines.append("some string")  # error: Type of "append" is partially unknown

# Good
banner_lines: list[str] = []
banner_lines.append("some string")  # OK
```

## Pre-commit Hooks

The repo uses pre-commit hooks installed via `make prepare`. Hooks run per package:

| Scope | Format Target | Check Target |
|-------|--------------|--------------|
| Root (`kimi-cli`) | `make format-kimi-cli` | `make check-kimi-cli` |
| `packages/kosong` | `make format-kosong` | `make check-kosong` |
| `packages/kaos` | `make format-pykaos` | `make check-pykaos` |

`make check-*` runs:
1. `ruff check`
2. `ruff format --check`
3. `pyright`
4. `ty check || true` (non-blocking)

If **any** of steps 1–3 fail, the hook (and commit) fails.
