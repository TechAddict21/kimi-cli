from __future__ import annotations

import json
import logging
from typing import Any

import aiofiles
from fastapi import APIRouter

from analytics_web.api.sessions import _find_session_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/sessions/{work_dir_hash}/{session_id}/token-usage")
async def get_token_usage(work_dir_hash: str, session_id: str) -> list[dict[str, Any]]:
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return []

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return []

    points: list[dict[str, Any]] = []
    turn_index = -1
    cum_input = 0
    cum_output = 0

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

            elif msg_type == "StatusUpdate":
                tu = payload.get("token_usage")
                if isinstance(tu, dict):
                    inp = (
                        int(tu.get("input_other", 0))
                        + int(tu.get("input_cache_read", 0))
                        + int(tu.get("input_cache_creation", 0))
                    )
                    out = int(tu.get("output", 0))
                    cum_input += inp
                    cum_output += out
                    points.append(
                        {
                            "turn_index": max(turn_index, 0),
                            "timestamp": ts,
                            "input_tokens": inp,
                            "output_tokens": out,
                            "cumulative_input": cum_input,
                            "cumulative_output": cum_output,
                        }
                    )

    return points
