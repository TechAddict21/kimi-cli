# Soul — Reviewer

The `Reviewer` class (`src/kimi_cli/soul/reviewer.py`) reviews the agent's final response before it is presented to the user. It is a fail-open component: any error or timeout returns `None`, allowing the response through.

## Trigger timing

The reviewer runs **once per turn at turn resolution**, only when the assistant produces a final response with **no tool calls** (i.e., the agent loop is exiting). It does **NOT** trigger during intermediate steps where the assistant calls tools and loops back.

Automatic triggering happens in `KimiSoul._turn()` at the "3. TURN RESOLUTION" stage (`kimisoul.py` ~line 1248).

## Configuration

Controlled by `Config` (`src/kimi_cli/config.py`):

- `reviewer_enabled: bool = False` — Enables the automatic reviewer flow.
- `reviewer_max_iterations: int = 3` — Maximum reviewer feedback loops per turn.

## Iteration tracking

`_reviewer_iterations` is reset to `0` at the start of each turn (`kimisoul.py` ~line 986). Each reviewer cycle increments it; once it reaches `reviewer_max_iterations`, further reviewer checks are skipped for that turn.

## Review flow (automatic)

1. Skip if no LLM is available (`runtime.llm is None`).
2. Skip if `_reviewer_iterations >= reviewer_max_iterations`.
3. Build a review prompt from `context.history` and the `final_message` text.
4. Call `generate()` with a system prompt `"You are a helpful code reviewer. Respond only with valid JSON."`.
5. Time out after 60 seconds.
6. Extract the first JSON object from the raw response (`_extract_json_object`).
7. Coerce fields into `ReviewResult`:
   - `need_changes` → `_coerce_bool()`
   - `feedback` / `refined_response` → `str()`
8. If `need_changes` is True:
   - Append `feedback` as a user message to context.
   - Continue the agent loop so the assistant revises.
   - This consumes one reviewer iteration.
9. If `refined_response` is provided (and `need_changes` is False):
   - Replace the final assistant message with the refined response.
10. Log the result and return it.

## Manual invocation

The `/review` slash command (`src/kimi_cli/soul/slash.py` ~line 357) lets the user manually trigger a review on the last assistant message. It creates a fresh `Reviewer` instance, runs `review()`, and if `refined_response` is returned, replaces the last assistant message in context history.

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
→ Read: src/kimi_cli/soul/kimisoul.py
→ Read: src/kimi_cli/soul/slash.py
→ Read: src/kimi_cli/config.py
→ Read: src/kimi_cli/prompts/__init__.py
→ Read: src/kimi_cli/soul/agent.py
