# Webhook Integration Reference

## Overview

`pc-kimi` can POST real-time lifecycle events to any HTTP endpoint. Every significant moment in the agent loop — session start, user prompt received, tool execution, LLM step complete, turn end, session exit — emits a structured JSON payload to your endpoint so downstream microservices can react, audit, log, or orchestrate without polling.

Webhooks are **fire-and-forget** (non-blocking). A slow or failing endpoint never stalls or crashes the CLI session.

---

## Enabling Webhooks

### CLI flag

```bash
pc-kimi --webhook-url-endpoint https://your-service.com/kimi/events
```

### Environment variable

```bash
export WEBHOOK_URL_ENDPOINT=https://your-service.com/kimi/events
pc-kimi
```

### Correlation ID (optional)

Pass an opaque ID that is echoed back verbatim in every payload. Use this to correlate events from a specific invocation with a job, request, or user in your system.

```bash
pc-kimi \
  --webhook-url-endpoint https://your-service.com/kimi/events \
  --webhook-session-id job-8f3a2c
```

Or via env:

```bash
export WEBHOOK_URL_ENDPOINT=https://your-service.com/kimi/events
export WEBHOOK_SESSION_ID=job-8f3a2c
pc-kimi
```

Both flags read from env vars if not provided directly (`WEBHOOK_URL_ENDPOINT`, `WEBHOOK_SESSION_ID`).

---

## HTTP Request Format

Every event is a `POST` to your endpoint.

### Headers

| Header | Value |
|--------|-------|
| `Content-Type` | `application/json` |
| `User-Agent` | `kimi-cli-webhook/1.0` |
| `X-Kimi-Event` | Event type string (e.g. `TurnBegin`) |
| `X-Kimi-Session` | Kimi internal session UUID |

### Body — base fields present on every payload

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `string` | Event name (see full list below) |
| `timestamp` | `float` | Unix epoch seconds (float, e.g. `1747480000.123`) |
| `hook_event_name` | `string` | Same as `event_type` — redundant but kept for consumers that key on this field |
| `session_id` | `string` | Kimi internal session UUID |
| `cwd` | `string` | Working directory when the event fired |
| `webhook_session_id` | `string?` | Your correlation ID — present only if `--webhook-session-id` was passed |

---

## Complete Event Reference

### 10 active event types (3 removed: `PreToolUse`, `SubagentStart`, `SubagentStop`)

---

### `SessionStart`

Fired once when the session initialises.

**Source:** `src/kimi_cli/cli/__init__.py` → `SessionStart` hook trigger

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source` | `string` | `"startup"` (new session) or `"resume"` (existing session) |

**Example:**
```json
{
  "event_type": "SessionStart",
  "timestamp": 1747480000.0,
  "hook_event_name": "SessionStart",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "source": "startup"
}
```

---

### `SessionEnd`

Fired when the session exits (normal exit, Ctrl+C, or error).

**Source:** `src/kimi_cli/cli/__init__.py` → finally block

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `reason` | `string` | Always `"exit"` currently |

**Example:**
```json
{
  "event_type": "SessionEnd",
  "timestamp": 1747480900.0,
  "hook_event_name": "SessionEnd",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "reason": "exit"
}
```

---

### `TurnBegin`

Fired the moment the CLI starts processing a user message. Resets per-turn token accumulators.

**Source:** `src/kimi_cli/soul/kimisoul.py` → `run()` → after `wire_send(TurnBegin(...))`

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `user_input` | `string` | The raw prompt text (empty string if input was non-text content) |
| `model` | `string?` | LLM model name; `null` if LLM not yet initialised |

**Example:**
```json
{
  "event_type": "TurnBegin",
  "timestamp": 1747480010.0,
  "hook_event_name": "TurnBegin",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "user_input": "Refactor the auth module to use JWT",
  "model": "kimi-latest"
}
```

---

### `UserPromptSubmit`

Fired just before `TurnBegin`, while the hook engine can still **block** the prompt. If a blocking hook is present and fires, `TurnBegin` will never follow.

**Source:** `src/kimi_cli/soul/kimisoul.py` → `run()` → `UserPromptSubmit` hook trigger

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `prompt` | `string` | The prompt text |

**Example:**
```json
{
  "event_type": "UserPromptSubmit",
  "timestamp": 1747480009.8,
  "hook_event_name": "UserPromptSubmit",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "prompt": "Refactor the auth module to use JWT"
}
```

---

### `PostToolUse`

Fired after a tool call succeeds. Contains the full input and output.

**Source:** `src/kimi_cli/soul/toolset.py` → `PostToolUse` hook trigger (fire-and-forget)

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `string` | e.g. `"Bash"`, `"ReadFile"`, `"WriteFile"`, `"WebSearch"` |
| `tool_input` | `object` | Exact parameters passed to the tool |
| `tool_output` | `string` | The tool's text output (may be truncated in logs) |
| `tool_call_id` | `string` | Internal ID linking this result to its LLM tool-call request |

**Example:**
```json
{
  "event_type": "PostToolUse",
  "timestamp": 1747480045.2,
  "hook_event_name": "PostToolUse",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "tool_name": "Bash",
  "tool_input": { "command": "pytest tests/ -q" },
  "tool_output": "12 passed in 1.43s",
  "tool_call_id": "toolu_01XYZ"
}
```

---

### `PostToolUseFailure`

Fired after a tool call throws an error.

**Source:** `src/kimi_cli/soul/toolset.py` → `PostToolUseFailure` hook trigger (fire-and-forget)

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `string` | Tool that failed |
| `tool_input` | `object` | Parameters that were passed |
| `error` | `string` | Error message |
| `tool_call_id` | `string` | Internal ID |

**Example:**
```json
{
  "event_type": "PostToolUseFailure",
  "timestamp": 1747480046.0,
  "hook_event_name": "PostToolUseFailure",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "tool_name": "Bash",
  "tool_input": { "command": "invalid-cmd" },
  "error": "command not found: invalid-cmd",
  "tool_call_id": "toolu_01XYZ"
}
```

---

### `Stop`

Fired after the agent finishes responding (all tool calls resolved, final message emitted). A blocking Stop hook can inject follow-up instructions back into the agent.

**Source:** `src/kimi_cli/soul/kimisoul.py` → `run()` → `Stop` hook trigger

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `stop_hook_active` | `bool` | `true` if this Stop was triggered by a previous Stop hook's injected text (re-trigger guard) |

**Example:**
```json
{
  "event_type": "Stop",
  "timestamp": 1747480090.0,
  "hook_event_name": "Stop",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "stop_hook_active": false
}
```

---

### `StopFailure`

Fired when the agent loop crashes with an unrecoverable error.

**Source:** `src/kimi_cli/soul/kimisoul.py` → exception handler

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `error_type` | `string` | Python exception class name |
| `error_message` | `string` | Exception message string |

**Example:**
```json
{
  "event_type": "StopFailure",
  "timestamp": 1747480091.0,
  "hook_event_name": "StopFailure",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "error_type": "APIStatusError",
  "error_message": "Rate limit exceeded"
}
```

---

### `TurnEnd`

Fired after `Stop` completes and the turn is fully resolved. Contains accumulated token usage for the entire turn (across all LLM steps).

**Source:** `src/kimi_cli/soul/kimisoul.py` → `run()` → after `wire_send(TurnEnd())`

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `model` | `string?` | LLM model name |
| `turn_input_tokens` | `int` | Total input tokens consumed across all steps this turn |
| `turn_output_tokens` | `int` | Total output tokens generated across all steps this turn |
| `turn_total_tokens` | `int` | `turn_input_tokens + turn_output_tokens` |
| `context_tokens` | `int` | Current context window size in tokens after this turn |

**Example:**
```json
{
  "event_type": "TurnEnd",
  "timestamp": 1747480095.0,
  "hook_event_name": "TurnEnd",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "model": "kimi-latest",
  "turn_input_tokens": 4200,
  "turn_output_tokens": 860,
  "turn_total_tokens": 5060,
  "context_tokens": 22400
}
```

---

### `CliReady`

Fired immediately after `TurnEnd`, once the shell is ready to accept the next user input. Carries the same usage fields as `TurnEnd`. Use this as the "done" signal if your microservice is waiting to dispatch a follow-up prompt.

**Source:** `src/kimi_cli/soul/kimisoul.py` → `run()` → after `write_file_log("CLI_READY_FOR_INPUT", ...)`

**Extra fields:** identical to `TurnEnd`

**Example:**
```json
{
  "event_type": "CliReady",
  "timestamp": 1747480095.1,
  "hook_event_name": "CliReady",
  "session_id": "a1b2c3d4-...",
  "cwd": "/Users/user/project",
  "webhook_session_id": "job-8f3a2c",
  "model": "kimi-latest",
  "turn_input_tokens": 4200,
  "turn_output_tokens": 860,
  "turn_total_tokens": 5060,
  "context_tokens": 22400
}
```

---

### `PreCompact`

Fired before context compaction runs (either auto-triggered by token threshold or manually with `/compact`).

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `trigger` | `string` | `"auto"`, `"manual"`, or `"manual-with-prompt"` |
| `token_count` | `int` | Context size in tokens before compaction |

---

### `PostCompact`

Fired after context compaction completes.

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `trigger` | `string` | Same as `PreCompact` |
| `estimated_token_count` | `int` | Estimated context size after compaction |

---

### `Notification`

Fired when a system notification is delivered into the LLM context.

**Extra fields:**

| Field | Type | Description |
|-------|------|-------------|
| `sink` | `string` | Always `"llm"` |
| `notification_type` | `string` | Notification category |
| `title` | `string` | Notification title |
| `body` | `string` | Notification body text |
| `severity` | `string` | `"info"`, `"warning"`, `"error"` |

---

## Event Firing Order (single turn)

```
SessionStart          ← once per session, on startup
  │
  ▼
UserPromptSubmit      ← user types a message
TurnBegin             ← processing starts
  │
  ├─ [LLM step 1]
  │    └─ PostToolUse / PostToolUseFailure  ← per tool call
  │
  ├─ [LLM step 2]
  │    └─ PostToolUse / PostToolUseFailure
  │  ...
  │
Stop                  ← agent finished responding
TurnEnd               ← turn closed (token counts available)
CliReady              ← shell ready for next input
  │
  ▼
UserPromptSubmit      ← next turn starts...
  ...

SessionEnd            ← once per session, on exit
```

**Note:** If compaction fires mid-turn:
```
PreCompact → PostCompact
```
These can appear inside a turn, between LLM steps.

---

## Ignored Events (not sent to webhook)

| Event | Reason |
|-------|--------|
| `PreToolUse` | High-frequency, low-signal — fires before every tool including read-only lookups. Use `PostToolUse` + `PostToolUseFailure` for the outcome. |
| `SubagentStart` | Internal orchestration detail — subagents are spawned frequently for background tasks. |
| `SubagentStop` | Same as above. |

---

## Reliability & Delivery Guarantees

| Property | Behaviour |
|----------|-----------|
| **Delivery** | At-most-once. No retries. If your endpoint is down, the event is silently dropped. |
| **Ordering** | Events fire in the order they occur in the agent loop. Within a single asyncio task they are ordered; across concurrent tasks (e.g. fire-and-forget tool hooks) ordering is best-effort. |
| **Timeout** | HTTP POST has a 5-second timeout. Slow endpoints do not block the CLI. |
| **Errors** | All POST errors are logged at DEBUG level only. The CLI session is never interrupted. |
| **Backpressure** | None. Each event is a separate fire-and-forget `asyncio.create_task`. |

If you need at-least-once guarantees, run your endpoint behind a queue (e.g. accept the POST into Redis, SQS, or Kafka and process asynchronously).

---

## Microservice Integration Guide

### Minimal Express.js receiver (Node.js)

```js
const express = require('express');
const app = express();
app.use(express.json());

app.post('/kimi/events', (req, res) => {
  const { event_type, session_id, webhook_session_id, timestamp } = req.body;
  console.log(`[${event_type}] session=${session_id} corr=${webhook_session_id}`);

  switch (event_type) {
    case 'TurnEnd':
      console.log('tokens:', req.body.turn_input_tokens, '+', req.body.turn_output_tokens);
      break;
    case 'PostToolUse':
      console.log('tool:', req.body.tool_name, '→', req.body.tool_output?.slice(0, 80));
      break;
    case 'SessionEnd':
      console.log('session closed, reason:', req.body.reason);
      break;
  }

  res.sendStatus(200); // always respond fast — CLI does not wait
});

app.listen(8080, () => console.log('Webhook receiver on :8080'));
```

### Minimal FastAPI receiver (Python)

```python
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/kimi/events")
async def receive(request: Request):
    payload = await request.json()
    event = payload.get("event_type")
    corr  = payload.get("webhook_session_id", "—")
    ts    = payload.get("timestamp", 0)

    print(f"[{event}] corr={corr} ts={ts:.3f}")

    match event:
        case "TurnEnd" | "CliReady":
            print(f"  usage: in={payload['turn_input_tokens']} "
                  f"out={payload['turn_output_tokens']} "
                  f"ctx={payload['context_tokens']}")
        case "PostToolUse":
            print(f"  tool: {payload['tool_name']} → {str(payload.get('tool_output',''))[:80]}")
        case "StopFailure":
            print(f"  ERROR: {payload['error_type']}: {payload['error_message']}")

    return {"ok": True}  # body ignored by CLI — just respond 2xx fast

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
```

### Correlating events by your own ID

Your system starts a job and passes its own ID as `--webhook-session-id`:

```bash
JOB_ID=$(uuidgen)
pc-kimi \
  --webhook-url-endpoint http://localhost:8080/kimi/events \
  --webhook-session-id "$JOB_ID" \
  --prompt "Analyse and fix all failing tests"
```

Your receiver groups all events by `webhook_session_id` to reconstruct the full timeline of that job:

```
SessionStart  webhook_session_id=550e8400-...
TurnBegin     webhook_session_id=550e8400-...
PostToolUse   webhook_session_id=550e8400-...  tool=Bash
PostToolUse   webhook_session_id=550e8400-...  tool=WriteFile
Stop          webhook_session_id=550e8400-...
TurnEnd       webhook_session_id=550e8400-...  in=5100 out=920
CliReady      webhook_session_id=550e8400-...
SessionEnd    webhook_session_id=550e8400-...
```

### Computing cost (consumer side)

The CLI sends raw token counts. Apply your model's pricing on the consumer:

```python
# Example: hypothetical pricing
PRICE_PER_1K = {"kimi-latest": {"input": 0.0015, "output": 0.002}}

def compute_cost(payload: dict) -> float | None:
    if payload.get("event_type") not in ("TurnEnd", "CliReady"):
        return None
    model = payload.get("model", "kimi-latest")
    pricing = PRICE_PER_1K.get(model, {})
    input_cost  = payload["turn_input_tokens"]  / 1000 * pricing.get("input", 0)
    output_cost = payload["turn_output_tokens"] / 1000 * pricing.get("output", 0)
    return round(input_cost + output_cost, 6)
```

---

## Implementation Notes (for contributors)

### Source files

| File | Role |
|------|------|
| `src/kimi_cli/webhook/service.py` | Singleton URL store, async `fire()`, HTTP POST (httpx → urllib fallback) |
| `src/kimi_cli/webhook/__init__.py` | Re-exports `fire`, `initialize`, `is_active` |
| `src/kimi_cli/hooks/engine.py` | Calls `fire()` unconditionally inside `trigger()` before the early `total==0` return |
| `src/kimi_cli/soul/kimisoul.py` | `TurnBegin` / `TurnEnd` / `CliReady` events + token accumulators |
| `src/kimi_cli/cli/__init__.py` | `--webhook-url-endpoint`, `--webhook-session-id` options → `initialize()` |

### Adding a new event

1. Call `fire("YourEvent", { ...payload })` at the point in the codebase where it should fire.
2. The payload must include at minimum `hook_event_name`, `session_id`, `cwd` for consistency with hook events.
3. Document it in this file.

### Skipping an existing hook event from webhooks

Edit the `_WEBHOOK_SKIP` frozenset inside `HookEngine.trigger()` in `engine.py`:

```python
_WEBHOOK_SKIP: frozenset[str] = frozenset({"SubagentStart", "SubagentStop", "PreToolUse"})
```

### Token accumulator lifecycle

- Reset to `0` at every `TurnBegin` in `KimiSoul.run()`
- Incremented inside `KimiSoul._step()` at the usage update block (section 2e.5)
- Read at `TurnEnd` and `CliReady`
- Fields: `_turn_input_tokens: int`, `_turn_output_tokens: int`
