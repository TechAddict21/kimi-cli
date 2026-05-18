# Drill-Down Tree

_Edit this file to describe your project's knowledge areas, their associated
documentation, and the code files to read for each._

## Build & Quality
- **Build_Makefile.md** — Make targets for formatting, linting, type checking, testing, building, and pre-commit hooks
  → Read: Makefile
  → Read: .pre-commit-config.yaml
  → Read: packages/kaos/.pre-commit-config.yaml
  → Read: packages/kosong/.pre-commit-config.yaml
- **Build_TypeChecking.md** — Pyright and ty type checker configuration, common error patterns, and fixes
  → Read: src/kimi_cli/soul/reviewer.py
  → Read: pyproject.toml

## Core Runtime
- **Soul_Reviewer.md** — The Reviewer class that reviews agent final responses before presenting to user
  → Read: src/kimi_cli/soul/reviewer.py
  → Read: src/kimi_cli/prompts/__init__.py
  → Read: src/kimi_cli/soul/agent.py
