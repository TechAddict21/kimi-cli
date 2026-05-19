# Notifications

The notification system delivers external events (background tasks, file watchers, etc.) to the LLM as synthetic user messages wrapped in `<notification>` XML tags.

## Notification Messages

`build_notification_message(view, runtime)` constructs a `Message(role="user", content=[TextPart(...)])` containing:

```xml
<notification id="..." category="..." type="..." source_kind="..." source_id="...">
Title: ...
Severity: ...
<body>
</notification>
```

For task notifications from background tasks, it appends a `<task-notification>` block with task metadata and output tail.

## Detecting Notification Messages

`is_notification_message(message)` checks three conditions:
1. `message.role == "user"`
2. `len(message.content) == 1`
3. The single `TextPart` starts with `<notification ` after leading whitespace

This is used by:
- `normalize_history()` in `dynamic_injection.py` — prevents merging notification messages with adjacent user messages
- `KnowledgeFeederInjectionProvider` — excludes notifications when counting real user messages (Guard 3)

`extract_notification_ids(history)` scans all user messages for `<notification id="..."` and returns a set of IDs. Called on root soul init to ack already-seen notifications.

→ Read: src/kimi_cli/notifications/llm.py
→ Read: src/kimi_cli/soul/dynamic_injection.py
→ Read: src/kimi_cli/soul/dynamic_injections/knowledge_feeder.py
