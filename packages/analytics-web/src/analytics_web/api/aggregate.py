from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter

from analytics_web.config import get_sessions_root

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_cache: dict[str, tuple[dict[str, Any], float]] = {}
_CACHE_TTL = 60


@router.get("/stats")
async def get_aggregate_stats() -> dict[str, Any]:
    now = time.time()
    cached = _cache.get("stats")
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    sessions_root = get_sessions_root()
    empty = {
        "total_sessions": 0,
        "total_turns": 0,
        "total_tokens": {"input": 0, "output": 0},
        "total_duration_sec": 0,
        "tool_usage": [],
        "daily_usage": [],
        "per_project": [],
    }
    if not sessions_root.exists():
        _cache["stats"] = (empty, now)
        return empty

    total_sessions = 0
    total_turns = 0
    total_input_tokens = 0
    total_output_tokens = 0
    total_duration_sec = 0.0
    tool_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "error_count": 0})
    daily_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"sessions": 0, "turns": 0})
    project_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"sessions": 0, "turns": 0})

    for work_dir_hash_dir in sessions_root.iterdir():
        if not work_dir_hash_dir.is_dir():
            continue
        work_dir_name = work_dir_hash_dir.name

        for session_dir in work_dir_hash_dir.iterdir():
            if not session_dir.is_dir():
                continue
            wire_path = session_dir / "wire.jsonl"
            if not wire_path.exists():
                continue

            total_sessions += 1
            session_turns = 0
            session_input = 0
            session_output = 0
            first_ts = 0.0
            last_ts = 0.0
            session_date: str | None = None
            pending_tools: dict[str, str] = {}

            try:
                with wire_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            parsed = json.loads(line)
                        except Exception:
                            continue
                        msg = parsed.get("message", {})
                        if msg.get("type") == "metadata":
                            continue
                        ts = parsed.get("timestamp", 0)
                        msg_type = msg.get("type", "")
                        payload = msg.get("payload", {})

                        if first_ts == 0:
                            first_ts = ts
                            try:
                                dt = datetime.fromtimestamp(ts, tz=UTC)
                                session_date = dt.strftime("%Y-%m-%d")
                            except Exception:
                                pass
                        last_ts = ts

                        if msg_type == "TurnBegin":
                            session_turns += 1
                        elif msg_type == "ToolCall":
                            fn = payload.get("function")
                            if isinstance(fn, dict):
                                name = fn.get("name", "unknown")
                                tool_stats[name]["count"] += 1
                                tool_id = payload.get("id", "")
                                if tool_id:
                                    pending_tools[tool_id] = name
                        elif msg_type == "ToolResult":
                            tool_call_id = payload.get("tool_call_id", "")
                            rv = payload.get("return_value")
                            if isinstance(rv, dict) and rv.get("is_error"):
                                tool_name = pending_tools.get(tool_call_id)
                                if tool_name:
                                    tool_stats[tool_name]["error_count"] += 1
                            pending_tools.pop(tool_call_id, None)
                        elif msg_type == "StatusUpdate":
                            tu = payload.get("token_usage")
                            if isinstance(tu, dict):
                                session_input += (
                                    int(tu.get("input_other", 0))
                                    + int(tu.get("input_cache_read", 0))
                                    + int(tu.get("input_cache_creation", 0))
                                )
                                session_output += int(tu.get("output", 0))
            except Exception:
                continue

            total_turns += session_turns
            total_input_tokens += session_input
            total_output_tokens += session_output
            duration = last_ts - first_ts if last_ts > first_ts else 0
            total_duration_sec += duration

            if session_date:
                daily_stats[session_date]["sessions"] += 1
                daily_stats[session_date]["turns"] += session_turns
            project_stats[work_dir_name]["sessions"] += 1
            project_stats[work_dir_name]["turns"] += session_turns

    tool_usage = sorted(
        [
            {"name": name, "count": stats["count"], "error_count": stats["error_count"]}
            for name, stats in tool_stats.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )[:20]

    today = datetime.now(tz=UTC)
    daily_usage = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        entry = daily_stats.get(date_str, {"sessions": 0, "turns": 0})
        daily_usage.append(
            {
                "date": date_str,
                "sessions": entry["sessions"],
                "turns": entry["turns"],
            }
        )

    per_project = sorted(
        [
            {"work_dir": wd, "sessions": stats["sessions"], "turns": stats["turns"]}
            for wd, stats in project_stats.items()
        ],
        key=lambda x: x["turns"],
        reverse=True,
    )[:10]

    result = {
        "total_sessions": total_sessions,
        "total_turns": total_turns,
        "total_tokens": {"input": total_input_tokens, "output": total_output_tokens},
        "total_duration_sec": round(total_duration_sec, 2),
        "tool_usage": tool_usage,
        "daily_usage": daily_usage,
        "per_project": per_project,
    }
    _cache["stats"] = (result, now)
    return result


@router.get("/daily-usage")
async def get_daily_usage(days: int = 30) -> list[dict[str, Any]]:
    stats = await get_aggregate_stats()
    return stats["daily_usage"][-days:]


@router.get("/per-project")
async def get_per_project(top_n: int = 10) -> list[dict[str, Any]]:
    stats = await get_aggregate_stats()
    return stats["per_project"][:top_n]
