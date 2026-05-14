# Hooks Architecture

## Overview
Hooks are lifecycle event triggers that run shell commands or wire client callbacks at specific points in the Kimi CLI agent loop. They are defined in `~/.pc-kimi/config.toml` under `[[hooks]]`.

## Core Files

| File | Purpose |
|------|---------|
| `src/kimi_cli/hooks/config.py` | `HookDef` Pydantic model, `HookEventType` literal |
| `src/kimi_cli/hooks/engine.py` | `HookEngine` — matching, parallel execution, aggregation |
| `src/kimi_cli/hooks/runner.py` | `run_hook()` — subprocess execution, exit-code interpretation |
| `src/kimi_cli/hooks/events.py` | Payload builders for each of the 13 event types |
| `src/kimi_cli/hooks/__init__.py` | Public exports |

## 13 Hook Event Types

| Event | When Fired | Matcher Value | Can Block? |
|-------|-----------|---------------|------------|
| `PreToolUse` | Before a tool executes | Tool name | ✅ Yes |
| `PostToolUse` | After tool success | Tool name | No |
| `PostToolUseFailure` | After tool throws | Tool name | No |
| `UserPromptSubmit` | When user sends a prompt | Prompt text | ✅ Yes |
| `Stop` | After a successful turn | (empty) | ✅ Yes |
| `StopFailure` | When agent loop crashes | Exception class name | No |
| `SessionStart` | Session starts (startup/resume) | `"startup"` / `"resume"` | No |
| `SessionEnd` | Session exits | `"exit"` | No |
| `SubagentStart` | Subagent begins running | Subagent type name | No |
| `SubagentStop` | Subagent finishes | Subagent type name | No |
| `PreCompact` | Before context compaction | Trigger reason (`auto`/`manual`/`manual-with-prompt`) | No |
| `PostCompact` | After context compaction | Trigger reason | No |
| `Notification` | Notification delivered to LLM context | Notification type | No |

## Hook Execution Flow

1. **Matching**: `HookEngine.trigger()` regex-matches `matcher_value` against each hook's `matcher` field. Empty matcher matches everything.
2. **Deduplication**: Duplicate commands for the same event are deduplicated.
3. **Parallel execution**: All matched server-side hooks (subprocess) and wire-side hooks (client callback) run in parallel via `asyncio.gather`.
4. **Aggregation**: If **any** hook returns `block`, the whole batch is `block`.
5. **Fail-open**: Timeouts, subprocess crashes, and engine errors all default to `allow` (except telemetry, which runs outside the fail-open wrapper for security).

## Exit Code Semantics (Server-Side)

| Exit Code | Meaning |
|-----------|---------|
| `0` | Allow. If stdout contains valid JSON with `hookSpecificOutput.permissionDecision = "deny"`, treat as block. |
| `2` | Block. Reason taken from stderr. |
| Any other | Allow. |

## Integration Points

- `src/kimi_cli/app.py:330` — `HookEngine` created and injected into `KimiSoul` and `Runtime`
- `src/kimi_cli/cli/__init__.py` — `SessionStart` / `SessionEnd`
- `src/kimi_cli/soul/toolset.py` — `PreToolUse` (awaited), `PostToolUse`, `PostToolUseFailure`
- `src/kimi_cli/soul/kimisoul.py` — `UserPromptSubmit`, `Stop`, `StopFailure`, `Notification`, `PreCompact`, `PostCompact`
- `src/kimi_cli/subagents/runner.py` — `SubagentStart`, `SubagentStop`
- `src/kimi_cli/wire/server.py` — Wire hook subscription registration

## Debug File Logging

Every hook trigger is logged via `write_file_log()` (from `kimi_cli.utils.test_logger`) with title `HOOK_<event_name>`.

The `log_value` is a JSON string containing:
- `matcher_value`
- `input_data` (full payload sent to hooks)
- `hooks` (matched hook summaries: command, matcher, source, timeout)
- `results` (per-hook action, reason, exit_code, timed_out, stdout, stderr)
- `aggregated_action` and `aggregated_reason`
- `duration_ms`

Log file location: `~/.pc-kimi/logs/test_logs.jsonl` (or `KIMI_TEST_LOG_FILE` env override).
