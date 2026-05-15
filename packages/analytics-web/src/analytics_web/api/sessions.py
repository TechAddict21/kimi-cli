from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import APIRouter

from analytics_web.config import get_sessions_root

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _read_state(session_dir: Path) -> dict[str, Any]:
    state_path = session_dir / "state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _read_wire_header(wire_path: Path, max_bytes: int = 8192) -> tuple[str, int]:
    title = ""
    turn_count = 0
    try:
        with wire_path.open(encoding="utf-8") as f:
            bytes_read = 0
            for line in f:
                bytes_read += len(line.encode("utf-8"))
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except Exception:
                    continue
                msg = parsed.get("message", {})
                if msg.get("type") == "TurnBegin":
                    turn_count += 1
                    if turn_count == 1:
                        user_input = msg.get("payload", {}).get("user_input", "")
                        if isinstance(user_input, str):
                            title = user_input[:100]
                        elif isinstance(user_input, list) and user_input:
                            first = user_input[0]
                            if isinstance(first, dict):
                                title = str(first.get("text", ""))[:100]
                if bytes_read > max_bytes:
                    break
    except Exception:
        pass
    return title, turn_count


def _scan_session_dir(session_dir: Path, work_dir_hash: str) -> dict[str, Any] | None:
    if not session_dir.is_dir():
        return None

    wire_path = session_dir / "wire.jsonl"
    context_path = session_dir / "context.jsonl"
    state_path = session_dir / "state.json"

    wire_exists = wire_path.exists()
    context_exists = context_path.exists()
    state_exists = state_path.exists()

    mtimes: list[float] = []
    wire_size = context_size = state_size = 0
    if wire_exists:
        st = wire_path.stat()
        mtimes.append(st.st_mtime)
        wire_size = st.st_size
    if context_exists:
        st = context_path.stat()
        mtimes.append(st.st_mtime)
        context_size = st.st_size
    if state_exists:
        st = state_path.stat()
        mtimes.append(st.st_mtime)
        state_size = st.st_size

    session_state = _read_state(session_dir)
    title, turn_count = _read_wire_header(wire_path) if wire_exists else ("", 0)
    custom_title = session_state.get("custom_title")
    if custom_title:
        title = custom_title

    subagent_count = 0
    subagents_dir = session_dir / "subagents"
    if subagents_dir.is_dir():
        subagent_count = sum(1 for p in subagents_dir.iterdir() if p.is_dir())

    return {
        "session_id": session_dir.name,
        "work_dir_hash": work_dir_hash,
        "title": title,
        "last_updated": max(mtimes) if mtimes else 0,
        "turns": turn_count,
        "wire_size": wire_size,
        "context_size": context_size,
        "state_size": state_size,
        "total_size": wire_size + context_size + state_size,
        "subagent_count": subagent_count,
        "custom_title": custom_title,
        "archived": session_state.get("archived", False),
    }


def _list_sessions_sync() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    sessions_root = get_sessions_root()
    if not sessions_root.exists():
        return results

    for work_dir_hash_dir in sessions_root.iterdir():
        if not work_dir_hash_dir.is_dir():
            continue
        for session_dir in work_dir_hash_dir.iterdir():
            info = _scan_session_dir(session_dir, work_dir_hash_dir.name)
            if info:
                results.append(info)

    results.sort(key=lambda s: s["last_updated"], reverse=True)
    return results


@router.get("/sessions")
async def list_sessions() -> list[dict[str, Any]]:
    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _list_sessions_sync)


def _find_session_dir(work_dir_hash: str, session_id: str) -> Path | None:
    session_dir = get_sessions_root() / work_dir_hash / session_id
    if session_dir.is_dir():
        return session_dir
    return None


@router.get("/sessions/{work_dir_hash}/{session_id}/summary")
async def get_session_summary(work_dir_hash: str, session_id: str) -> dict[str, Any]:
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return {"error": "Session not found"}

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return {
            "turns": 0,
            "steps": 0,
            "tool_calls": 0,
            "errors": 0,
            "compactions": 0,
            "duration_sec": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }

    turns = steps = tool_calls = errors = compactions = 0
    input_tokens = output_tokens = 0
    first_ts = 0.0
    last_ts = 0.0

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
            if first_ts == 0:
                first_ts = ts
            last_ts = ts
            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            if msg_type == "TurnBegin":
                turns += 1
            elif msg_type == "StepBegin":
                steps += 1
            elif msg_type == "ToolCall":
                tool_calls += 1
            elif msg_type == "CompactionBegin":
                compactions += 1
            elif msg_type == "StepInterrupted":
                errors += 1
            elif msg_type == "ToolResult":
                rv = payload.get("return_value")
                if isinstance(rv, dict) and rv.get("is_error"):
                    errors += 1
            elif msg_type == "StatusUpdate":
                tu = payload.get("token_usage")
                if isinstance(tu, dict):
                    input_tokens += (
                        int(tu.get("input_other", 0))
                        + int(tu.get("input_cache_read", 0))
                        + int(tu.get("input_cache_creation", 0))
                    )
                    output_tokens += int(tu.get("output", 0))

    return {
        "turns": turns,
        "steps": steps,
        "tool_calls": tool_calls,
        "errors": errors,
        "compactions": compactions,
        "duration_sec": last_ts - first_ts if last_ts > first_ts else 0,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }
