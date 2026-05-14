# Kimi CLI — Agent Knowledge Base

> **MANDATORY**: Read this file first on every session before doing any codebase exploration.

## How to Use This Knowledge Base

This folder (`/Users/techaddict/kimi-cli/knowledge/`) contains distilled information about the codebase to save tokens and avoid redundant exploration.

### Step 1 — Read the Tree
**ALWAYS** read `/Users/techaddict/kimi-cli/knowledge/DRILL_DOWN_TREE.md` first.
It lists every knowledge file and its purpose. Use it to decide which files are relevant to your task.

### Step 2 — Read Relevant Knowledge Files
Before running `grep`, `Glob`, or reading source files, check if the topic already exists in this knowledge folder.

For Current knowledge areas check `DRILL_DOWN_TREE.md`

### Step 3 — Fall Back to Codebase Search
If the knowledge folder does **not** cover what you need, only then explore the codebase with `Grep`, `Glob`, `ReadFile`, or subagents.

### Step 4 — Update Knowledge After Task Completion
After completing a task, if you learned something new that would help future agents, add it to the relevant folder/file in this knowledge directory.
- Create new folders/files if needed
- Update `DRILL_DOWN_TREE.md` whenever you add new knowledge files
- Keep entries concise and factual

---

## Project Quick Facts

- **Name**: Kimi Code CLI (`pc-kimi` / `pc-kimi-cli`)
- **Type**: Python CLI agent for software engineering workflows
- **Package Manager**: `uv` (workspace monorepo)
- **Share Dir**: `~/.pc-kimi/` (config, logs, sessions, MCP config)
- **Entry**: `src/kimi_cli/__main__.py` → `src/kimi_cli/cli/__init__.py`
- **Main Loop**: `src/kimi_cli/soul/kimisoul.py` (`KimiSoul.run`)
- **Key Modules**:
  - `src/kimi_cli/soul/` — core runtime, context, compaction, approvals
  - `src/kimi_cli/tools/` — built-in tools (shell, file, web, agent, etc.)
  - `src/kimi_cli/ui/` — frontends (shell TUI, print, ACP, wire)
  - `src/kimi_cli/hooks/` — lifecycle hook system
  - `src/kimi_cli/wire/` — event transport between soul and UI
- **Workspace Packages**: `packages/kosong`, `packages/kaos`, `packages/kimi-code`, `sdks/kimi-sdk`
- **Tests**: `tests/`, `tests_e2e/`, `tests_ai/`
- **Lint/Format**: `ruff` | **Types**: `pyright` + `ty` | **Tests**: `pytest`
- **Line Length**: 100

## Quick Commands (via `uv`)

| Command | Purpose |
|---------|---------|
| `make prepare` | Sync deps + install git hooks |
| `uv run pc-kimi` | Run the CLI interactively |
| `uv run pytest tests -vv` | Run CLI tests |
| `make format` | Auto-format all code |
| `make check` | Run lint + type checks |
| `make test` | Run all test suites |
| `make build` | Build all packages |
| `make build-bin` | Build standalone executable |

## Key Lifecycle Logs (`write_file_log`)

The CLI writes structured JSONL entries (via `write_file_log`) for three critical lifecycle events:

| Event | `title` | Location | Trigger |
|-------|---------|----------|---------|
| **User submits prompt** | `USER_PROMPT_SUBMIT` | `src/kimi_cli/ui/shell/__init__.py` | Fires immediately after the shell UI receives non-empty user input from the prompt router. |
| **CLI stops the process** | `CLI_STOPPING` | `src/kimi_cli/ui/shell/__init__.py` | Fires in the `finally` block of `Shell.run()` when the interactive shell loop breaks (EOF, exit command, error, etc.). |
| **Ready for new input** | `CLI_READY_FOR_INPUT` | `src/kimi_cli/soul/kimisoul.py` | Fires at the end of `KimiSoul.run()` right after `TurnEnd()` is sent, signalling the soul has finished the turn and is ready for the next message. |

Log file path: `~/.pc-kimi/logs/test_logs.jsonl` (or `KIMI_TEST_LOG_FILE` env override).

---

*This file may be updated by agents when project-wide conventions change.*
