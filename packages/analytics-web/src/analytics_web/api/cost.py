from __future__ import annotations

import json
import logging
from typing import Any

import aiofiles
from fastapi import APIRouter

from analytics_web.api.sessions import _find_session_dir

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Default cost rates per 1M tokens (USD)
# These are approximate Claude Sonnet 4 rates
INPUT_RATE_PER_M = 3.00
OUTPUT_RATE_PER_M = 15.00


@router.get("/sessions/{work_dir_hash}/{session_id}/cost")
async def get_cost(
    work_dir_hash: str,
    session_id: str,
    input_rate: float = INPUT_RATE_PER_M,
    output_rate: float = OUTPUT_RATE_PER_M,
) -> dict[str, Any]:
    session_dir = _find_session_dir(work_dir_hash, session_id)
    if session_dir is None:
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "input_cost": 0,
            "output_cost": 0,
            "total_cost": 0,
            "per_turn": [],
        }

    wire_path = session_dir / "wire.jsonl"
    if not wire_path.exists():
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "input_cost": 0,
            "output_cost": 0,
            "total_cost": 0,
            "per_turn": [],
        }

    turn_index = -1
    per_turn: list[dict[str, Any]] = []
    total_input = 0
    total_output = 0
    turn_input = 0
    turn_output = 0

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

            if msg_type == "TurnBegin":
                if turn_index >= 0:
                    inp_cost = turn_input / 1_000_000 * input_rate
                    out_cost = turn_output / 1_000_000 * output_rate
                    per_turn.append(
                        {
                            "turn_index": turn_index,
                            "input_tokens": turn_input,
                            "output_tokens": turn_output,
                            "input_cost": round(inp_cost, 6),
                            "output_cost": round(out_cost, 6),
                            "total_cost": round(inp_cost + out_cost, 6),
                        }
                    )
                turn_index += 1
                turn_input = 0
                turn_output = 0

            elif msg_type == "StatusUpdate":
                tu = payload.get("token_usage")
                if isinstance(tu, dict):
                    inp = (
                        int(tu.get("input_other", 0))
                        + int(tu.get("input_cache_read", 0))
                        + int(tu.get("input_cache_creation", 0))
                    )
                    out = int(tu.get("output", 0))
                    turn_input += inp
                    turn_output += out
                    total_input += inp
                    total_output += out

    if turn_index >= 0:
        inp_cost = turn_input / 1_000_000 * input_rate
        out_cost = turn_output / 1_000_000 * output_rate
        per_turn.append(
            {
                "turn_index": turn_index,
                "input_tokens": turn_input,
                "output_tokens": turn_output,
                "input_cost": round(inp_cost, 6),
                "output_cost": round(out_cost, 6),
                "total_cost": round(inp_cost + out_cost, 6),
            }
        )

    total_input_cost = total_input / 1_000_000 * input_rate
    total_output_cost = total_output / 1_000_000 * output_rate

    return {
        "input_tokens": total_input,
        "output_tokens": total_output,
        "input_cost": round(total_input_cost, 6),
        "output_cost": round(total_output_cost, 6),
        "total_cost": round(total_input_cost + total_output_cost, 6),
        "per_turn": per_turn,
    }
