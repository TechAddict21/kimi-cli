from __future__ import annotations

from typing import Any


class SessionInfo:
    def __init__(
        self,
        session_id: str,
        work_dir_hash: str,
        work_dir: str | None,
        title: str,
        last_updated: float,
        turns: int,
        wire_size: int,
        context_size: int,
        state_size: int,
        total_size: int,
        subagent_count: int,
        custom_title: str | None,
        archived: bool,
    ) -> None:
        self.session_id = session_id
        self.work_dir_hash = work_dir_hash
        self.work_dir = work_dir
        self.title = title
        self.last_updated = last_updated
        self.turns = turns
        self.wire_size = wire_size
        self.context_size = context_size
        self.state_size = state_size
        self.total_size = total_size
        self.subagent_count = subagent_count
        self.custom_title = custom_title
        self.archived = archived

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "work_dir_hash": self.work_dir_hash,
            "work_dir": self.work_dir,
            "title": self.title,
            "last_updated": self.last_updated,
            "turns": self.turns,
            "wire_size": self.wire_size,
            "context_size": self.context_size,
            "state_size": self.state_size,
            "total_size": self.total_size,
            "subagent_count": self.subagent_count,
            "custom_title": self.custom_title,
            "archived": self.archived,
        }


class SessionSummary:
    def __init__(
        self,
        turns: int = 0,
        steps: int = 0,
        tool_calls: int = 0,
        errors: int = 0,
        compactions: int = 0,
        duration_sec: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        self.turns = turns
        self.steps = steps
        self.tool_calls = tool_calls
        self.errors = errors
        self.compactions = compactions
        self.duration_sec = duration_sec
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "turns": self.turns,
            "steps": self.steps,
            "tool_calls": self.tool_calls,
            "errors": self.errors,
            "compactions": self.compactions,
            "duration_sec": self.duration_sec,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class TurnTimeline:
    def __init__(
        self,
        turn_index: int,
        timestamp: float,
        user_input: str,
        steps: list[dict[str, Any]],
    ) -> None:
        self.turn_index = turn_index
        self.timestamp = timestamp
        self.user_input = user_input
        self.steps = steps

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "timestamp": self.timestamp,
            "user_input": self.user_input,
            "steps": self.steps,
        }


class TokenUsagePoint:
    def __init__(
        self,
        turn_index: int,
        timestamp: float,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        self.turn_index = turn_index
        self.timestamp = timestamp
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "timestamp": self.timestamp,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


class ToolStat:
    def __init__(self, name: str, count: int, error_count: int, avg_duration_ms: float) -> None:
        self.name = name
        self.count = count
        self.error_count = error_count
        self.avg_duration_ms = avg_duration_ms

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "count": self.count,
            "error_count": self.error_count,
            "avg_duration_ms": self.avg_duration_ms,
        }


class StepLatency:
    def __init__(
        self,
        turn_index: int,
        step_index: int,
        llm_duration_ms: float,
        tool_duration_ms: float,
        tool_name: str | None,
    ) -> None:
        self.turn_index = turn_index
        self.step_index = step_index
        self.llm_duration_ms = llm_duration_ms
        self.tool_duration_ms = tool_duration_ms
        self.tool_name = tool_name

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "step_index": self.step_index,
            "llm_duration_ms": self.llm_duration_ms,
            "tool_duration_ms": self.tool_duration_ms,
            "tool_name": self.tool_name,
        }


class CostBreakdown:
    def __init__(
        self,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        total_cost: float,
        per_turn: list[dict[str, Any]],
    ) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.input_cost = input_cost
        self.output_cost = output_cost
        self.total_cost = total_cost
        self.per_turn = per_turn

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_cost": self.input_cost,
            "output_cost": self.output_cost,
            "total_cost": self.total_cost,
            "per_turn": self.per_turn,
        }


class AggregateStats:
    def __init__(
        self,
        total_sessions: int,
        total_turns: int,
        total_tokens: dict[str, int],
        total_duration_sec: float,
        tool_usage: list[dict[str, Any]],
        daily_usage: list[dict[str, Any]],
        per_project: list[dict[str, Any]],
    ) -> None:
        self.total_sessions = total_sessions
        self.total_turns = total_turns
        self.total_tokens = total_tokens
        self.total_duration_sec = total_duration_sec
        self.tool_usage = tool_usage
        self.daily_usage = daily_usage
        self.per_project = per_project

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_turns": self.total_turns,
            "total_tokens": self.total_tokens,
            "total_duration_sec": self.total_duration_sec,
            "tool_usage": self.tool_usage,
            "daily_usage": self.daily_usage,
            "per_project": self.per_project,
        }
