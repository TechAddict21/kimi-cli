from __future__ import annotations

import json
import logging
from typing import Any

import aiofiles
from fastapi import APIRouter

from analytics_web.api.sessions import _find_session_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sessions/{work_dir_hash}/{session_id}/timeline")
async def get_timeline(work_dir_hash: str, session_id: str) -> list[dict[str, Any]]:
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return []

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return []

    turns: list[dict[str, Any]] = []
    current_turn: dict[str, Any] | None = None
    current_step: dict[str, Any] | None = None
    turn_index = 0
    step_index = 0

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
            ts = parsed.get("timestamp", 0)
            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            if msg_type == "TurnBegin":
                if current_turn:
                    if current_step:
                        current_turn["steps"].append(current_step)
                        current_step = None
                    turns.append(current_turn)
                current_turn = {
                    "turn_index": turn_index,
                    "timestamp": ts,
                    "user_input": str(payload.get("user_input", ""))[:200],
                    "duration_ms": 0,
                    "steps": [],
                }
                turn_index += 1
                step_index = 0

            elif msg_type == "StepBegin":
                if current_step and current_turn is not None:
                    current_turn["steps"].append(current_step)
                current_step = {
                    "step_index": step_index,
                    "timestamp": ts,
                    "type": "llm",
                    "duration_ms": 0,
                    "tool_calls": [],
                    "error": None,
                }
                step_index += 1

            elif msg_type == "ToolCall":
                if current_step:
                    current_step["type"] = "tool"
                    fn = payload.get("function", {})
                    current_step["tool_calls"].append(
                        {
                            "tool_name": fn.get("name", "unknown")
                            if isinstance(fn, dict)
                            else "unknown",
                            "timestamp": ts,
                            "duration_ms": 0,
                        }
                    )
                    tool_start_ts = ts

            elif msg_type == "ToolResult":
                if current_step and current_step["tool_calls"]:
                    last_tool = current_step["tool_calls"][-1]
                    last_tool["duration_ms"] = (ts - tool_start_ts) * 1000
                    rv = payload.get("return_value")
                    if isinstance(rv, dict) and rv.get("is_error"):
                        current_step["error"] = rv.get("error", "ToolError")
                    else:
                        last_tool["error"] = None

            elif msg_type == "StepInterrupted":
                if current_step:
                    current_step["error"] = payload.get("error_type", "Interrupted")

            elif msg_type == "TurnEnd":
                if current_step and current_turn is not None:
                    current_turn["steps"].append(current_step)
                    current_step = None
                if current_turn is not None:
                    current_turn["duration_ms"] = (ts - current_turn["timestamp"]) * 1000
                    turns.append(current_turn)
                    current_turn = None

    if current_turn:
        if current_step:
            current_turn["steps"].append(current_step)
        turns.append(current_turn)

    return turns
