# Type Checking — Pyright & ty

The project uses **pyright** as the primary type checker and **ty** as a secondary, non-blocking checker. Both target `pythonVersion = "3.14"`.

## Configuration

- `pyproject.toml` → `[tool.pyright]`:
  - `typeCheckingMode = "standard"`
  - `strict = ["src/kimi_cli/**/*.py"]` — strict mode for CLI sources
  - `include` covers `src/**/*.py`, `tests/**/*.py`, `tests_e2e/**/*.py`, `tests_ai/scripts/**/*.py`
- `pyproject.toml` → `[tool.ty.environment]` and `[tool.ty.src]`:
  - Same include paths as pyright

## Common patterns & fixes

### `dict.get()` on `cast(dict[str, object], ...)` can still infer as `Unknown`

Even after casting a parsed JSON value to `dict[str, object]`, pyright may infer the result of `.get()` as partially `Unknown` because `dict.get` has an overloaded signature where the default value influences the return type.

**Problematic pattern:**
```python
parsed = cast(dict[str, object], some_json)
need_changes = _coerce_bool(parsed.get("need_changes", False))  # pyright error
```

**Fix:** Extract the `.get()` result into an explicitly annotated `object` intermediate before passing to helpers.

```python
parsed = cast(dict[str, object], some_json)

need_changes_raw: object = parsed.get("need_changes", False)
feedback_raw: object = parsed.get("feedback", "")
review_result = ReviewResult(
    need_changes=_coerce_bool(need_changes_raw),
    feedback=str(feedback_raw),
)
```

→ Read: src/kimi_cli/soul/reviewer.py
