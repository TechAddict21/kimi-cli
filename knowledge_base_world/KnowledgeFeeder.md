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

## Logging

All feeder events are written as structured JSONL to `~/.pc-kimi/logs/feeder/feeder_logs.jsonl` via `write_feeder_log()`.

→ Read: src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py
→ Read: src/kimi_cli/utils/test_logger.py
