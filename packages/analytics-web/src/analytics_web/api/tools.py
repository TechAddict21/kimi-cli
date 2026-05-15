from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

import aiofiles
from fastapi import APIRouter

from analytics_web.api.sessions import _find_session_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sessions/{work_dir_hash}/{session_id}/tool-stats")
async def get_tool_stats(work_dir_hash: str, session_id: str) -> dict[str, Any]:
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return {"tools": [], "total_calls": 0, "total_errors": 0}

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return {"tools": [], "total_calls": 0, "total_errors": 0}

    tool_counts: dict[str, int] = defaultdict(int)
    tool_errors: dict[str, int] = defaultdict(int)
    tool_durations: dict[str, list[float]] = defaultdict(list)
    pending_tools: dict[str, tuple[str, float]] = {}
    total_calls = 0
    total_errors = 0

    async with aiofiles.open(wire_path, encoding="utf-8") as f:
        async for line in f:
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
            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})
            ts = parsed.get("timestamp", 0)

            if msg_type == "ToolCall":
                fn = payload.get("function")
                if isinstance(fn, dict):
                    name = fn.get("name", "unknown")
                    tool_counts[name] += 1
                    total_calls += 1
                    tool_id = payload.get("id", "")
                    if tool_id:
                        pending_tools[tool_id] = (name, ts)

            elif msg_type == "ToolResult":
                tool_call_id = payload.get("tool_call_id", "")
                if tool_call_id in pending_tools:
                    name, start_ts = pending_tools.pop(tool_call_id)
                    rv = payload.get("return_value")
                    is_error = isinstance(rv, dict) and rv.get("is_error")
                    if is_error:
                        tool_errors[name] += 1
                        total_errors += 1
                    tool_durations[name].append((ts - start_ts) * 1000)

    tools = []
    for name, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
        durations = tool_durations.get(name, [])
        avg_dur = sum(durations) / len(durations) if durations else 0
        tools.append(
            {
                "name": name,
                "count": count,
                "error_count": tool_errors.get(name, 0),
                "avg_duration_ms": round(avg_dur, 1),
            }
        )

    return {
        "tools": tools,
        "total_calls": total_calls,
        "total_errors": total_errors,
    }
