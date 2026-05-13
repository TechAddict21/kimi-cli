# Fork Change Log

Short notes on changes made to the upstream Kimi CLI repo.

---

## 2026-05-13 — Rebrand: `.kimi` → `.pc-kimi`, command `kimi` → `pc-kimi`

**Goal:** Rename user data directory and CLI command for this fork.

**Global constants added** (`src/kimi_cli/constant.py`):
- `SHARE_DIR_NAME = ".pc-kimi"`
- `CLI_COMMAND = "pc-kimi"`
- `CLI_COMMAND_ALT = "pc-kimi-cli"`
- `LOG_FILE_NAME = f"{CLI_COMMAND}.log"`

**Entry points** (`pyproject.toml`):
- `kimi` → `pc-kimi`
- `kimi-cli` → `pc-kimi-cli`

**Source files updated to use constants** (no hardcoded strings):
- `share.py`, `skill/__init__.py`, `soul/agent.py`, `tools/plan/heroes.py`
- `app.py`, `cli/__init__.py`, `cli/mcp.py`, `soul/toolset.py`
- `ui/shell/*.py`, `ui/print/__init__.py`, `plugin/manager.py`, `__main__.py`

**Tests updated** to expect new paths/commands:
- `tests/`, `tests_e2e/`, `scripts/cleanup_tmp_sessions.py`

**Docs folder left untouched** per request.

**Fix:** Added missing module-level import `from kimi_cli.constant import ...` in `cli/__init__.py` — f-strings in `typer.Option(help=...)` annotations need the name available at module scope for Python 3.14 annotation evaluation.

**UI simplifications** (`src/kimi_cli/ui/shell/`):
- Removed welcome banner/logo panel (`_print_welcome_info` function and its call removed from `shell/__init__.py`).
- Removed toolbar tips from the prompt (no more keyboard shortcut hints like ctrl-x, shift-tab, ctrl-o, etc. in `prompt.py`).
- Removed dirty git indicator (`±`) from the git status badge.
- Removed `/feedback` tip from welcome info (`app.py`).

---
