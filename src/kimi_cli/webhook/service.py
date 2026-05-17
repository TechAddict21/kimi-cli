from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from kimi_cli import logger

_webhook_url: str | None = None
_webhook_session_id: str | None = None


def initialize(url: str | None, session_id: str | None = None) -> None:
    global _webhook_url, _webhook_session_id
    _webhook_url = url.strip() if url else None
    _webhook_session_id = session_id.strip() if session_id else None


def is_active() -> bool:
    return bool(_webhook_url)


async def _post(url: str, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "kimi-cli-webhook/1.0",
        "X-Kimi-Event": str(payload.get("event_type", "")),
        "X-Kimi-Session": str(payload.get("session_id", "")),
    }
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, content=body, headers=headers)
        return
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Webhook POST (httpx) failed ({}): {}", url, exc)
        return

    # stdlib fallback — blocking, run in thread pool
    try:
        import urllib.request

        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, urllib.request.urlopen, req)
    except Exception as exc:
        logger.debug("Webhook POST (urllib) failed ({}): {}", url, exc)


def fire(event_type: str, payload: dict[str, Any]) -> None:
    """Fire-and-forget POST to the configured webhook URL.

    No-op when no URL is configured. Never raises — all errors are logged at
    DEBUG level so webhook failures never interrupt the CLI session.
    """
    url = _webhook_url
    if not url:
        return

    full_payload: dict[str, Any] = {
        "event_type": event_type,
        "timestamp": time.time(),
        **({"webhook_session_id": _webhook_session_id} if _webhook_session_id else {}),
        **payload,
    }
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_post(url, full_payload))
        # Keep a strong reference so GC doesn't collect the pending task.
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    except RuntimeError:
        # No running event loop (sync context) — silently skip.
        pass
