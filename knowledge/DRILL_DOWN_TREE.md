- Hooks (Folder)
  - ARCHITECTURE.md — Hooks system overview: 13 event types, execution flow, integration points, debug logging

- System (Root)
  - WEBHOOKS.md — Webhook integration reference: all 10 active event types, full payload schemas, firing order, token usage fields, microservice receiver examples (Node.js + Python), cost calculation, skip list, implementation notes

- linting (Folder)
  - COMMON_ERRORS.md — Common ruff/pyright errors (E501, F841, list[Unknown] inference) and fixes, pre-commit hook structure

- logging (Folder)
  - UTILITIES.md — write_file_log utility, usage across codebase, loguru logger reference

- Reviewer (Folder)

- run_restart_project (Folder)
  - HOW_TO_RUN.md — How to run, test, format, and build the project via uv

- System (Folder)
  - FLOW.md — Full system architecture flow: init, request, feeder, completer, reviewer lifecycle with Mermaid diagrams
  - FEEDER_COMPLETER.md — Knowledge Feeder & Completer reference: all logic, scoring, logging, web dashboard API and frontend
