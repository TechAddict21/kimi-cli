from __future__ import annotations

import json
import logging
from typing import Any

import aiofiles
from fastapi import APIRouter

from analytics_web.api.sessions import _find_session_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sessions/{work_dir_hash}/{session_id}/latency")
async def get_latency(work_dir_hash: str, session_id: str) -> list[dict[str, Any]]:
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return []

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return []

    steps: list[dict[str, Any]] = []
    turn_index = -1
    step_index = -1
    step_start = 0.0
    tool_start = 0.0
    current_tool_name: str | None = None
    in_step = False

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

            if msg_type == "TurnBegin":
                turn_index += 1
                step_index = -1
                in_step = False

            elif msg_type == "StepBegin":
                step_index += 1
                step_start = ts
                in_step = True
                current_tool_name = None

            elif msg_type in ("ContentPart",) or (
                msg_type == "StatusUpdate" and payload.get("token_usage")
            ):
                pass

            elif msg_type == "ToolCall":
                fn = payload.get("function")
                if isinstance(fn, dict):
                    current_tool_name = fn.get("name", "unknown")
                tool_start = ts

            elif msg_type == "ToolResult":
                if current_tool_name and in_step:
                    tool_duration = (ts - tool_start) * 1000
                    llm_duration = (tool_start - step_start) * 1000
                    steps.append(
                        {
                            "turn_index": turn_index,
                            "step_index": step_index,
                            "llm_duration_ms": round(llm_duration, 1),
                            "tool_duration_ms": round(tool_duration, 1),
                            "tool_name": current_tool_name,
                        }
                    )
                    step_start = ts
                    current_tool_name = None

    return steps
