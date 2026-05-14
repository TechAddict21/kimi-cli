import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_DEFAULT_LOG_PATH = Path.home() / ".pc-kimi" / "logs" / "test_logs.jsonl"


def _get_test_log_path() -> Path:
    """Return the path to the test log file."""
    log_path = Path(os.getenv("KIMI_TEST_LOG_FILE", _DEFAULT_LOG_PATH))
    log_path.parent.mkdir(parents=True, exist_ok=True)
    return log_path


def write_file_log(title: str, log_value: str, **extra: Any) -> None:
    """Append a structured log entry to the log file.

    Each entry is a JSON line with the following fields:
        - title:      A short title/tag for the log event.
        - log_value:  The actual log content / message.
        - log_time:   ISO-8601 timestamp in UTC.
        - extra:      Optional additional key-value pairs.
    """
    entry: dict[str, Any] = {
        "title": title,
        "log_value": log_value,
        "log_time": datetime.now(UTC).isoformat(),
    }
    if extra:
        entry["extra"] = extra

    log_path = _get_test_log_path()
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
