from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kosong.utils.test_logger import write_file_log

__all__ = ["write_file_log", "write_review_log", "write_feeder_log", "write_trace_time_entry"]


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


def write_feeder_log(title: str, log_value: str, **extra: Any) -> None:
    """Append a structured log entry to the feeder-specific log file."""
    log_path = Path.home() / ".pc-kimi" / "logs" / "feeder" / "feeder_logs.jsonl"
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


def write_trace_time_entry(
    session_dir: Path,
    title: str,
    start_time: float,
    end_time: float,
    context_length: int,
    turn_id: str | None = None,
) -> None:
    """Append a structured timing entry to the session's trace_time.json.

    The file is stored as a JSON array of objects, each representing a
    timed phase (feeder, completer, peer_review, turn, step_llm, etc.).
    """
    trace_file = session_dir / "trace_time.json"
    entries: list[dict[str, Any]] = []
    if trace_file.exists():
        try:
            with open(trace_file, encoding="utf-8") as f:
                entries = json.load(f)
        except (OSError, json.JSONDecodeError):
            entries = []

    entries.append(
        {
            "title": title,
            "start_time": datetime.fromtimestamp(start_time, tz=UTC).isoformat(),
            "end_time": datetime.fromtimestamp(end_time, tz=UTC).isoformat(),
            "total_seconds": round(end_time - start_time, 3),
            "context_length": context_length,
            "turn_id": turn_id,
        }
    )

    from kimi_cli.utils.io import atomic_json_write

    atomic_json_write(entries, trace_file)
