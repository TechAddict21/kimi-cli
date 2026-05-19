# Dynamic Injections

The soul supports pluggable **dynamic injection providers** that insert extra prompt content before each LLM step. Providers handle their own throttling and can access full runtime state via the `soul` parameter.

## Base Framework

`DynamicInjection` is a frozen dataclass with `type: str` and `content: str`. `DynamicInjectionProvider` is an ABC with three lifecycle hooks:

- `get_injections(history, soul) -> list[DynamicInjection]` — called every step
- `on_context_compacted()` — called after history compaction; providers reset throttling state
- `on_afk_changed(enabled)` — called when afk mode toggles

→ Read: src/kimi_cli/soul/dynamic_injection.py

## Provider Registry

Providers are registered in `KimiSoul.__init__` in fixed order:

1. `PlanModeInjectionProvider`
2. `KnowledgeFeederInjectionProvider`
3. `AfkModeInjectionProvider` (skipped if `config.skip_afk_prompt_injection`)

Additional providers can be registered at runtime via `KimiSoul.add_injection_provider()`.

`_collect_injections()` iterates all providers, catches failures per-provider (fail-open), and sets `_feeder_injected_this_turn = True` if any `knowledge_feeder` injection is present.

→ Read: src/kimi_cli/soul/kimisoul.py

## Plan Mode Provider

Injects read-only workflow reminders while plan mode is active. Throttled by scanning history backwards: counts assistant messages since the last plan reminder and only injects every `_TURN_INTERVAL = 5` assistant turns. Every `_FULL_EVERY_N = 5`th injection is the full reminder; others are sparse.

On manual toggle (`consume_pending_plan_activation_injection()`), injects a one-shot activation reminder (full if no plan exists, reentry if a plan file exists).

Subagents are excluded because they typically lack EnterPlanMode/ExitPlanMode tools.

→ Read: src/kimi_cli/soul/dynamic_injections/plan_mode.py

## AFK Mode Provider

Injects away-from-keyboard guidance (`_AFK_PROMPT_ROOT`) when `soul.is_afk` and `soul.is_afk_flag` are both true. Only fires once until reset by `on_context_compacted()` or `on_afk_changed()`. Subagents are excluded.

Also defines `AFK_DISABLED_REMINDER` for when the user returns.

→ Read: src/kimi_cli/soul/dynamic_injections/afk_mode.py
