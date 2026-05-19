# Drill-Down Tree

_Edit this file to describe your project's knowledge areas, their associated
documentation, and the code files to read for each._

## Build & Quality
- **Build_Makefile.md** — Make targets for formatting, linting, type checking, testing, building, and pre-commit hooks (ruff line length 100)
  → Read: Makefile
  → Read: .pre-commit-config.yaml
  → Read: packages/kaos/.pre-commit-config.yaml
  → Read: packages/kosong/.pre-commit-config.yaml
  → Read: pyproject.toml
- **Build_TypeChecking.md** — Pyright and ty type checker configuration, common error patterns, and fixes
  → Read: pyproject.toml
  → Read: ty.toml

## Core Runtime
- **Soul_Reviewer.md** — The Reviewer class that reviews agent final responses before presenting to user
  → Read: src/kimi_cli/soul/reviewer.py
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: src/kimi_cli/soul/slash.py
  → Read: src/kimi_cli/config.py
  → Read: src/kimi_cli/prompts/__init__.py
  → Read: src/kimi_cli/soul/agent.py
- **DynamicInjections.md** — Pluggable prompt injection framework (plan mode, AFK, knowledge feeder) and provider lifecycle
  → Read: src/kimi_cli/soul/dynamic_injection.py
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: src/kimi_cli/soul/dynamic_injections/plan_mode.py
  → Read: src/kimi_cli/soul/dynamic_injections/afk_mode.py
- **KnowledgeFeeder.md** — Knowledge base feeder (classifies and injects matched code) and post-turn knowledge completer (updates KB via subagent)
  → Read: src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: src/kimi_cli/utils/kb_io.py
  → Read: src/kimi_cli/subagents/runner.py
  → Read: src/kimi_cli/utils/test_logger.py
- **Soul_TraceTiming.md** — Trace timing system: `trace_time.json` per session, epoch timestamp requirement, and `time.time()` vs `time.monotonic()` distinction
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: src/kimi_cli/utils/test_logger.py
- **Soul_RetryRecovery.md** — Step retry with tenacity, connection recovery via `RetryableChatProvider.on_retryable_error`, and OAuth refresh on 401 status errors
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: packages/kosong/src/kosong/chat_provider/__init__.py
- **Soul_RalphLoop.md** — Automated iteration mode that replays the original prompt with CONTINUE/STOP choice tags until the task is complete or max moves reached
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: src/kimi_cli/config.py
  → Read: tests/core/test_kimisoul_ralph_loop.py

## System Architecture
- **System_Flow.md** — End-to-end architecture flow: startup init, user request phases, agent loop, post-turn completer and reviewer
  → Read: knowledge/FLOW.md
  → Read: src/kimi_cli/soul/kimisoul.py
  → Read: src/kimi_cli/soul/dynamic_injection.py

## Notifications
- **Notifications.md** — Synthetic user messages for external events, detection via is_notification_message, and history normalization
  → Read: src/kimi_cli/notifications/llm.py
  → Read: src/kimi_cli/soul/dynamic_injection.py
  → Read: src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py
