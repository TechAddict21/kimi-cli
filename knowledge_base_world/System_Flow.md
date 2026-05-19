# System Architecture Flow

High-level end-to-end flow of a user request through the Kimi CLI system, based on `knowledge/FLOW.md`.

## Startup & Init

1. **CLI Entry** — `src/kimi_cli/cli/__init__.py` parses flags (`--session`, `--model`, `--agent`, ...).
2. **Load Config** — `~/.pc-kimi/config.toml` via `src/kimi_cli/config.py`.
3. **Session** — `Session.find`, `Session.continue_`, or `Session.create` (`src/kimi_cli/session.py`).
4. **Runtime** — `Runtime.create` bundles config, session, builtins (`src/kimi_cli/soul/agent.py`).
5. **Load Agent** — YAML spec + system prompt (`src/kimi_cli/agentspec.py`).
6. **Context Restore** — History from `context.jsonl` (`src/kimi_cli/soul/context.py`).
7. **KimiSoul** — Created and ready (`src/kimi_cli/soul/kimisoul.py`).
8. **Feeder lazy init** — First turn triggers `get_injections()`.

## User Request Flow (Per Turn)

### Phase 1: Slash / Hook
- Parse slash command (`src/kimi_cli/soul/slash.py`); if matched, execute and return.
- Fire `UserPromptSubmit` hook.

### Phase 2: Agent Turn
- `_turn()` → `_agent_loop()` → `_step()` (`kimisoul.py`).
- **Each step**:
  1. Notification delivery (pending background results).
  2. **Dynamic Injection** — `_collect_injections()` calls providers (plan mode, AFK, knowledge feeder).
     - Knowledge Feeder (`src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py`) lazy-inits `knowledge_base_world/`, reads `DRILL_DOWN_TREE.md`, classifies user request via LLM, reads matched code files (capped at 8 KiB), and injects as `<system-reminder>`.
  3. `normalize_history()` merges injected content with the original user message.
  4. LLM call via `kosong.step(system_prompt, toolset, history)`.
  5. If tool calls exist: execute tools (`src/kimi_cli/soul/toolset.py`), append results, loop again.
  6. If no tool calls: exit loop → `TurnOutcome`.

### Phase 3: Post-Turn
- Log `FEEDER_HELPED` unconditionally.
- `_maybe_run_knowledge_completer()`:
  - Guard: skip if no tool calls were made in the turn, or if `knowledge_base_world/` does not exist.
  - Fire-and-forget background task launching `knowledge-completer` subagent.
  - Subagent reads/updates KB files and `DRILL_DOWN_TREE.md`.
  - Logs `COMPLETER_UPDATED` + true/false based on file mtime changes.
- **Reviewer** (optional, `reviewer_enabled`):
  - Runs at turn resolution, only when assistant has **no tool calls**.
  - If `need_changes`: inject feedback as user message and re-enter agent loop (up to `reviewer_max_iterations`).
  - If `refined_response`: replace final assistant message directly.
- Stop hook fires.

### Phase 4: Response
- `TurnEnd` event sent to UI.
- User sees the result.

## Component Relationships

- **KimiSoul** orchestrates: Runtime, Context, Agent, Toolset, Dynamic Injections, Post-Processing, UI.
- **Knowledge Feeder** ↔ `knowledge_base_world/` (read) and logs (`feeder_logs.jsonl`).
- **Knowledge Completer** ↔ `knowledge_base_world/` (read/write) and logs.
- **Reviewer** → logs (`reviewer_logs.jsonl`).

## Key Files

- `src/kimi_cli/soul/kimisoul.py` — Main loop: `run()`, `_turn()`, `_agent_loop()`, `_step()`.
- `src/kimi_cli/soul/dynamic_injection.py` — Dynamic injection framework and provider lifecycle.
- `src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py` — Feeder classify + inject logic.
- `src/kimi_cli/soul/reviewer.py` — Response review before presenting to user.
- `src/kimi_cli/subagents/runner.py` — Subagent runner for completer.
- `knowledge/FLOW.md` — Authoritative visual architecture document.

→ Read: knowledge/FLOW.md
→ Read: src/kimi_cli/soul/kimisoul.py
→ Read: src/kimi_cli/soul/dynamic_injection.py
→ Read: src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py
→ Read: src/kimi_cli/soul/reviewer.py
→ Read: src/kimi_cli/subagents/runner.py
