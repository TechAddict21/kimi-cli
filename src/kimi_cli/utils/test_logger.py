from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kosong.utils.test_logger import write_file_log

__all__ = ["write_file_log", "write_review_log"]


def write_review_log(title: str, log_value: str, **extra: Any) -> None:
    """Append a structured log entry to the reviewer-specific log file."""
    log_path = Path.home() / ".pc-kimi" / "logs" / "reviewer_logs.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry: dict[str, Any] = {
        "title": title,
        "log_value": log_value,
        "log_time": datetime.now(UTC).isoformat(),
    }
    if extra:
        entry["extra"] = extra
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
