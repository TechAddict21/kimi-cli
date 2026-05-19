# Knowledge Feeder

`KnowledgeFeederInjectionProvider` injects relevant codebase knowledge from `knowledge_base_world/` into the LLM context before the first real user message of a turn. It reduces token waste by pre-reading files listed in `DRILL_DOWN_TREE.md` instead of having the agent explore cold.

## Initialization

`_ensure_init(work_dir)` locates or creates `knowledge_base_world/` with default `UNDERSTANDING.md` and `DRILL_DOWN_TREE.md` templates. Also writes a `.gitignore` to exclude transient lockfiles. If the work dir is missing, falls back to `/workspace` with a log event.

## Classification Flow

1. `_load_tree()` parses `DRILL_DOWN_TREE.md` into `{entry_path: [read_paths]}` via `_parse_tree_for_read_paths()`. Supports both old indented format and markdown header format.
2. `_classify_relevance(user_text, soul)` sends a lightweight LLM call with a system prompt `"You are a code knowledge relevance classifier..."` and the tree content. Expects a JSON array of entry paths. Strips markdown fences and validates the result is a list.
3. `_read_relevant_code()` resolves glob/file paths (sandboxed to `work_dir`, capped at `_MAX_GLOB_EXPANSION = 5`), reads content, and formats as markdown sections. Total injection is capped at `MAX_INJECTION_BYTES = 8192`.

## Guards in `get_injections()`

The provider has multiple guards to avoid redundant work:

| Guard | Condition | Log Event |
|-------|-----------|-----------|
| Same turn | `soul.turn_id == self._last_turn_id` | `FEEDER_SKIP_SAME_TURN` |
| Subagent | `not soul.is_root` and type not in `FEEDER_ALLOWED_SUBAGENT_TYPES` | `FEEDER_SKIP_SUBAGENT` |
| No tree | `_load_tree()` fails | `FEEDER_NO_TREE` |
| Not first message | `user_msg_count > 1` (non-notification user messages) | `FEEDER_SKIP_NOT_FIRST_MSG` |
| No user text | No real user message found in history | `FEEDER_NO_USER_TEXT` |
| Cache hit | Same text and prior injection exists | `FEEDER_CACHE_HIT` |
| No matches | Classifier returns `[]` | `FEEDER_CLASSIFY_EMPTY` |
| No code | Resolved paths yield no content | `FEEDER_NO_CODE` |

Allowed subagent types: `explore` (read-only roles where repeated lookups would be wasteful).

## Injection Format

```
IMPORTANT: The following files have already been read and their content is provided below. Do NOT read/re-read these files. Use this context directly as the source of truth.
Knowledge entries matched: <entries>

## <entry>
### `<rel_path>`
```
<code>
```
```

## Knowledge Completer

After every turn with tool calls on the root soul, `_maybe_run_knowledge_completer()` in `kimisoul.py` launches a `knowledge-completer` subagent to analyze the conversation and update the KB.

### Incremental vs Full Analysis

- `_last_completer_history_len` tracks how much history was already analyzed. On the next run, only new messages (`history[last_len:]`) are sent (incremental mode).
- After context compaction, `_last_completer_history_len` resets to `0`, so the next run sends the last 40 messages (full mode).
- Both modes cap at 40 messages for safety.

### Prompts

- **Incremental**: "Analyze ONLY the new conversation above. What additional knowledge was gained in this turn? Update DRILL_DOWN_TREE.md and create/update knowledge files... Do NOT duplicate existing entries."
- **Full**: "Analyze the session above. What new knowledge was gained? What was missed? Update DRILL_DOWN_TREE.md and create/update knowledge files..."

### Locking & Concurrency

Uses `kb_try_lock(kb_dir)` to prevent concurrent completer runs. If another process holds the lock, the run is skipped with `COMPLETER_SKIP` + "another completer holds the KB lock".

### Change Detection

Before running the subagent, the completer records `{rel_path: mtime}` for every file in `knowledge_base_world/`. After the subagent finishes, it re-scans and compares mtimes:

| Change | Marker | Example |
|--------|--------|---------|
| New file | `+` | `+Build_TypeChecking.md` |
| Modified file | `~` | `~KnowledgeFeeder.md` |

Result is logged as `COMPLETER_UPDATED` with `files` and `reason` fields.

### Guards

- Skip if not root soul.
- Skip if no tool calls occurred in the turn.
- Skip if `knowledge_base_world/` does not exist.
- Skip if KB lock is held by another completer.

### FEEDER_HELPED Telemetry

After the completer finishes, `kimisoul.py` logs `FEEDER_HELPED`:

```python
no_exploration = self._exploration_calls_this_turn == 0
completer_filled_gap = completer_updated is True
feeder_helped = no_exploration or completer_filled_gap
```

The feeder "helped" if the agent did not need to explore files directly, or if the completer successfully added missing knowledge.

→ Read: src/kimi_cli/soul/kimisoul.py
→ Read: src/kimi_cli/utils/kb_io.py
→ Read: src/kimi_cli/subagents/runner.py

## Logging

All feeder events are written as structured JSONL to `~/.pc-kimi/logs/feeder/feeder_logs.jsonl` via `write_feeder_log()`.

→ Read: src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py
→ Read: src/kimi_cli/utils/test_logger.py
