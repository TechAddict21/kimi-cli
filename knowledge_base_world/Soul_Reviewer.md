# Soul — Reviewer

The `Reviewer` class (`src/kimi_cli/soul/reviewer.py`) reviews the agent's final response before it is presented to the user. It is a fail-open component: any error or timeout returns `None`, allowing the response through.

## Review flow

1. Skip if no LLM is available (`runtime.llm is None`).
2. Build a review prompt from `context.history` and the `final_message` text.
3. Call `generate()` with a system prompt `"You are a helpful code reviewer. Respond only with valid JSON."`.
4. Time out after 60 seconds.
5. Extract the first JSON object from the raw response (`_extract_json_object`).
6. Coerce fields into `ReviewResult`:
   - `need_changes` → `_coerce_bool()`
   - `feedback` / `refined_response` → `str()`
7. Log the result and return it.

## Data model

```python
@dataclass
class ReviewResult:
    need_changes: bool       # True if the response needs revision
    feedback: str            # Specific feedback for the LLM
    refined_response: str    # A refined version for minor fixes
```

## Helpers

- `_extract_json_object(text)` — Scans text for the first `{` or `[`, then uses `json.JSONDecoder.raw_decode` to parse it. Tolerates markdown fences, preamble, and trailing prose.
- `_coerce_bool(value)` — Coerces JSON-decoded values to `bool`. Stringy `"false"`, `"0"`, `""`, `"no"`, `"null"`, `"none"` are treated as `False`.

## Prompt template

The review prompt is loaded from `src/kimi_cli/prompts/reviewer.md` and imported via:

```python
from kimi_cli.prompts import REVIEWER
```

→ Read: src/kimi_cli/soul/reviewer.py
→ Read: src/kimi_cli/prompts/__init__.py
→ Read: src/kimi_cli/soul/agent.py
