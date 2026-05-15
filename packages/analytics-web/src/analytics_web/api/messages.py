from __future__ import annotations

import json
import logging
from typing import Any

import aiofiles
from fastapi import APIRouter, Query

from analytics_web.api.sessions import _find_session_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sessions/{work_dir_hash}/{session_id}/messages")
async def get_messages(work_dir_hash: str, session_id: str) -> dict[str, Any]:
    """Return context.jsonl messages (conversation history)."""
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return {"total": 0, "messages": []}

    context_path = session_dir / "context.jsonl"
    if not context_path.exists():
        return {"total": 0, "messages": []}

    messages: list[dict[str, Any]] = []
    index = 0
    system_prompt = ""

    async with aiofiles.open(context_path, encoding="utf-8") as f:
        async for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            role = msg.get("role", "")

            if role == "_system_prompt":
                system_prompt = msg.get("content", "")
                continue

            msg["index"] = index
            index += 1
            messages.append(msg)

    return {
        "total": len(messages),
        "system_prompt": system_prompt,
        "messages": messages,
    }


@router.get("/sessions/{work_dir_hash}/{session_id}/conversation")
async def get_conversation(work_dir_hash: str, session_id: str) -> list[dict[str, Any]]:
    """Return structured turn-by-turn conversation from wire.jsonl.

    Each turn has:
      turn_index, timestamp, user_input (string),
      steps: [{content_parts: [{type, text, think, ...}],
               tool_calls: [{id, name, arguments}],
               tool_results: [{tool_call_id, output, is_error}],
               step_index, timestamp}]
    """
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
    pending_tool_ids: dict[str, int] = {}

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
                    turns.append(current_turn)
                user_input = payload.get("user_input", "")
                user_text = _extract_text(user_input)
                current_turn = {
                    "turn_index": turn_index,
                    "timestamp": ts,
                    "user_input": user_text,
                    "user_input_raw": user_input,
                    "steps": [],
                }
                turn_index += 1
                step_index = 0
                current_step = None

            elif msg_type == "SteerInput":
                if current_turn:
                    steer = payload.get("user_input", "")
                    steer_text = _extract_text(steer)
                    if current_turn["user_input"]:
                        current_turn["user_input"] += "\n" + steer_text
                    else:
                        current_turn["user_input"] = steer_text

            elif msg_type == "StepBegin":
                if current_step and current_turn is not None:
                    current_turn["steps"].append(current_step)
                current_step = {
                    "step_index": step_index,
                    "timestamp": ts,
                    "content_parts": [],
                    "tool_calls": [],
                    "tool_results": [],
                }
                step_index += 1

            elif msg_type == "ContentPart":
                if current_step is not None:
                    part = dict(payload)
                    # Remove event-level type wrapper; keep part.type
                    part_copy = {k: v for k, v in part.items() if k != "event"}
                    current_step["content_parts"].append(part_copy)

            elif msg_type == "ToolCall":
                if current_step is not None:
                    fn = payload.get("function", {})
                    tc_id = payload.get("id", "")
                    args_raw = fn.get("arguments", "{}") if isinstance(fn, dict) else "{}"
                    try:
                        parsed_args = json.loads(args_raw)
                    except Exception:
                        parsed_args = args_raw
                    tc = {
                        "id": tc_id,
                        "name": fn.get("name", "unknown") if isinstance(fn, dict) else "unknown",
                        "arguments": parsed_args,
                        "arguments_raw": args_raw,
                        "timestamp": ts,
                    }
                    current_step["tool_calls"].append(tc)
                    if tc_id:
                        pending_tool_ids[tc_id] = step_index - 1

            elif msg_type == "ToolResult":
                if current_step is not None:
                    call_id = payload.get("tool_call_id", "")
                    rv = payload.get("return_value", {})
                    output_raw = rv.get("output", "") if isinstance(rv, dict) else ""
                    output_text = _extract_text(output_raw)
                    is_error = rv.get("is_error", False) if isinstance(rv, dict) else False
                    current_step["tool_results"].append(
                        {
                            "tool_call_id": call_id,
                            "output": output_text,
                            "is_error": is_error,
                            "timestamp": ts,
                        }
                    )
                    pending_tool_ids.pop(call_id, None)

            elif msg_type == "StatusUpdate":
                tu = payload.get("token_usage")
                if tu and current_turn is not None:
                    inp = (
                        int(tu.get("input_other", 0))
                        + int(tu.get("input_cache_read", 0))
                        + int(tu.get("input_cache_creation", 0))
                    )
                    out = int(tu.get("output", 0))
                    current_turn.setdefault("token_usage", {"input": 0, "output": 0})
                    current_turn["token_usage"]["input"] += inp
                    current_turn["token_usage"]["output"] += out

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


@router.get("/sessions/{work_dir_hash}/{session_id}/raw-events")
async def get_raw_events(
    work_dir_hash: str,
    session_id: str,
    type: str | None = Query(None, description="Filter by event type"),
    search: str | None = Query(None, description="Search in payload text"),
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=5000),
) -> dict[str, Any]:
    """Return raw wire.jsonl events with optional filtering."""
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return {"total": 0, "events": [], "filtered_total": 0}

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return {"total": 0, "events": [], "filtered_total": 0}

    all_events: list[dict[str, Any]] = []
    index = 0

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
            ev_type = msg.get("type", "")
            if type and ev_type != type:
                continue
            payload = msg.get("payload", {})
            if search:
                payload_str = json.dumps(payload)
                if search.lower() not in payload_str.lower():
                    continue
            all_events.append(
                {
                    "index": index,
                    "timestamp": parsed.get("timestamp", 0),
                    "type": ev_type,
                    "payload": payload,
                }
            )
            index += 1

    filtered_total = len(all_events)
    events = all_events[offset : offset + limit]

    return {
        "total": index,
        "filtered_total": filtered_total,
        "events": events,
    }


@router.get("/sessions/{work_dir_hash}/{session_id}/event-types")
async def get_event_types(work_dir_hash: str, session_id: str) -> list[str]:
    """Return distinct event types in this session."""
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return []

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return []

    seen: set[str] = set()
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
            seen.add(msg.get("type", ""))

    return sorted(seen)


def _extract_text(content: Any) -> str:
    """Extract plain text from ContentPart array, string, or other format."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "think" in item:
                    parts.append(str(item["think"]))
                elif "refusal" in item:
                    parts.append(str(item["refusal"]))
                elif "image_url" in item or "audio_url" in item or "video_url" in item:
                    parts.append(f"[{item.get('type', 'media')}]")
                else:
                    parts.append(json.dumps(item))
            else:
                parts.append(str(item))
        return "\n".join(parts)
    return str(content) if content else ""
