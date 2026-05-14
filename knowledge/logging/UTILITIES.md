# Logging Utilities

## `write_file_log`

**Location**: `kimi_cli.utils.test_logger` (re-exported from `kosong.utils.test_logger`)

**Signature**:
```python
def write_file_log(title: str, log_value: str, **extra: Any) -> None
```

**Behavior**:
- Appends a single JSON line to a log file.
- Default path: `~/.pc-kimi/logs/test_logs.jsonl`
- Override path via `KIMI_TEST_LOG_FILE` environment variable.
- Creates parent directories automatically.

**Entry schema**:
```json
{
  "title": "REVIEWER_PROMPT",
  "log_value": "...",
  "log_time": "2026-05-14T08:45:00.123456+00:00",
  "extra": { ... }
}
```

## Current Usage in Codebase

| File | Title | Purpose |
|------|-------|---------|
| `src/kimi_cli/soul/reviewer.py` | `REVIEWER_PROMPT` | Logs the review prompt sent to LLM |
| `src/kimi_cli/soul/reviewer.py` | `REVIEWER_RAW_RESPONSE` | Logs the raw LLM review response |
| `src/kimi_cli/soul/reviewer.py` | `REVIEWER_RESULT` | Logs parsed review result JSON |
| `src/kimi_cli/soul/reviewer.py` | `REVIEWER_ERROR` | Logs review failures |
| `src/kimi_cli/hooks/engine.py` | `HOOK_<EventName>` | Logs every hook trigger with full payload and results |

## Project-Wide Logger

The project uses `loguru` via `from kimi_cli import logger`.
