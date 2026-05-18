# ruff: noqa: E501
"""Analytics API endpoints for feeder and completer statistics."""

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from starlette.responses import HTMLResponse

FEEDER_LOG_PATH = Path.home() / ".pc-kimi" / "logs" / "feeder" / "feeder_logs.jsonl"

router = APIRouter()


def _read_feeder_logs() -> list[dict[str, Any]]:
    """Read all feeder log entries from the JSONL file."""
    if not FEEDER_LOG_PATH.exists():
        return []
    try:
        entries: list[dict[str, Any]] = []
        with open(FEEDER_LOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries
    except (json.JSONDecodeError, OSError):
        return []


@router.get("/api/analytics/feeder-stats")
async def feeder_stats() -> dict[str, Any]:
    """Return aggregate feeder and completer analytics."""
    entries = _read_feeder_logs()

    total_entries = len(entries)
    title_counts: Counter[str] = Counter()
    matched_entries_set: set[str] = set()
    inject_count = 0
    completions = {"start": 0, "done": 0, "failed": 0, "skipped": 0}
    feeder_classify = {"total": 0, "matched": 0, "empty": 0, "failed": 0}
    total_injection_bytes = 0
    latest_timestamp: str | None = None

    for entry in entries:
        title = entry.get("title", "")
        title_counts[title] += 1

        ts = entry.get("log_time", "")
        if ts and (latest_timestamp is None or ts > latest_timestamp):
            latest_timestamp = ts

        if title == "FEEDER_INJECT":
            inject_count += 1
            extra: dict[str, Any] = entry.get("extra") or {}
            total_injection_bytes += int(extra.get("injection_len", 0))
            log_value = entry.get("log_value", "")
            _, _, rest = log_value.partition("entries=")
            if rest:
                matched_entries_set.update(e.strip("'\"[] ") for e in rest.split(","))

        elif title == "FEEDER_CLASSIFY_RESULT":
            feeder_classify["matched"] += 1
        elif title == "FEEDER_CLASSIFY_EMPTY":
            feeder_classify["empty"] += 1
        elif title == "FEEDER_CLASSIFY_FAILED":
            feeder_classify["failed"] += 1

        elif title == "COMPLETER_START":
            completions["start"] += 1
        elif title == "COMPLETER_DONE":
            completions["done"] += 1
        elif title == "COMPLETER_FAILED":
            completions["failed"] += 1
        elif title == "COMPLETER_SKIP":
            completions["skipped"] += 1

    feeder_classify["total"] = (
        feeder_classify["matched"] + feeder_classify["empty"] + feeder_classify["failed"]
    )

    total_turns = title_counts.get("FEEDER_TURN_START", 0)
    tree_loads = title_counts.get("FEEDER_TREE_LOADED", 0)

    # Parse FEEDER_HELPED
    feeder_helped_true = 0
    feeder_helped_false = 0
    total_exploration_calls: int = 0
    for entry in entries:
        if entry.get("title") == "FEEDER_HELPED":
            if entry.get("log_value") == "true":
                feeder_helped_true += 1
            else:
                feeder_helped_false += 1
            fh_extra: dict[str, Any] = entry.get("extra") or {}
            total_exploration_calls += int(fh_extra.get("exploration_calls", 0))

    # Parse COMPLETER_UPDATED
    completer_updated_true = 0
    completer_updated_false = 0
    completer_reasons: list[str] = []
    for entry in entries:
        if entry.get("title") == "COMPLETER_UPDATED":
            if entry.get("log_value") == "true":
                completer_updated_true += 1
            else:
                completer_updated_false += 1
            cu_extra: dict[str, Any] = entry.get("extra") or {}
            if cu_extra.get("reason"):
                completer_reasons.append(str(cu_extra["reason"]))

    return {
        "total_entries": total_entries,
        "latest_entry": latest_timestamp or "N/A",
        "feeder": {
            "total_turns_processed": total_turns,
            "tree_loads": tree_loads,
            "classifications": feeder_classify,
            "injections": inject_count,
            "total_injection_bytes": total_injection_bytes,
            "matched_knowledge_entries": sorted(matched_entries_set),
            "cache_hits": title_counts.get("FEEDER_CACHE_HIT", 0),
            "helped": {"true": feeder_helped_true, "false": feeder_helped_false},
            "total_exploration_calls": total_exploration_calls,
        },
        "completer": {
            "starts": completions["start"],
            "completed": completions["done"],
            "failed": completions["failed"],
            "skipped": completions["skipped"],
            "updated": {"true": completer_updated_true, "false": completer_updated_false},
            "reasons": completer_reasons[-10:],
        },
        "errors": {
            "classify_errors": feeder_classify["failed"],
            "completer_errors": completions["failed"],
        },
    }


@router.get("/api/analytics/timeline")
async def feeder_timeline() -> dict[str, list[Any]]:
    """Return chronological timeline of feeder events."""
    entries = _read_feeder_logs()
    timeline: list[Any] = []
    for entry in entries[-100:]:
        timeline.append(
            {
                "time": entry.get("log_time", ""),
                "event": entry.get("title", ""),
                "detail": entry.get("log_value", ""),
                "extra": entry.get("extra"),
            }
        )
    return {"events": timeline}


@router.post("/api/analytics/reset-feeder-logs")
async def reset_feeder_logs():
    """Delete the feeder log file, resetting all analytics."""
    if FEEDER_LOG_PATH.exists():
        try:
            FEEDER_LOG_PATH.unlink()
            return {"success": True, "message": "Feeder logs cleared"}
        except OSError as e:
            return {"success": False, "message": str(e)}
    return {"success": True, "message": "No logs to clear"}


@router.post("/api/analytics/reset-all-sessions")
async def reset_all_sessions():
    """Delete all session directories."""
    from kimi_cli.metadata import load_metadata

    meta = load_metadata()
    removed = 0
    for wd in meta.work_dirs:
        session_dir = wd.sessions_dir
        if session_dir.exists():
            try:
                shutil.rmtree(session_dir)
                removed += 1
            except OSError:
                pass
    meta.work_dirs = []
    from kimi_cli.metadata import save_metadata

    save_metadata(meta)
    return {
        "success": True,
        "message": f"Cleared {removed} session director{'y' if removed == 1 else 'ies'}",
    }


_HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Feeder &amp; Completer Analytics</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; padding: 24px; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 24px; color: #58a6ff; }}
  h2 {{ font-size: 1.1rem; margin: 20px 0 12px; color: #f0f6fc; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 20px; }}
  .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
  .card .label {{ font-size: 0.75rem; text-transform: uppercase; color: #8b949e; margin-bottom: 4px; }}
  .card .value {{ font-size: 1.8rem; font-weight: 600; color: #f0f6fc; }}
  .card .sub {{ font-size: 0.85rem; color: #8b949e; margin-top: 4px; }}
  .good {{ color: #3fb950; }}
  .warn {{ color: #d29922; }}
  .bad {{ color: #f85149; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
  th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #21262d; font-size: 0.9rem; }}
  th {{ color: #8b949e; font-weight: 500; }}
  .timeline {{ max-height: 400px; overflow-y: auto; font-family: 'SF Mono', 'Cascadia Code', monospace; font-size: 0.8rem; }}
  .timeline div {{ padding: 4px 0; border-bottom: 1px solid #21262d; }}
  .timeline .time {{ color: #8b949e; }}
  ._0 {{ color: #58a6ff; }} ._1 {{ color: #3fb950; }} ._2 {{ color: #d29922; }} ._3 {{ color: #f85149; }}
  a {{ color: #58a6ff; text-decoration: none; }} a:hover {{ text-decoration: underline; }}
  .nav {{ margin-bottom: 20px; }} .nav a {{ margin-right: 16px; }}
</style>
</head>
<body>
<h1>📊 Feeder &amp; Completer Analytics</h1>
<div id="root"></div>
<script>
// Auth: read token from URL once, strip it (so it never lands in browser
// history, server logs, or referrer headers), persist via sessionStorage
// for refreshes, then send as Authorization: Bearer on every fetch. The
// server's AuthMiddleware only honors Bearer (and a GET query fallback);
// query tokens leak via URL and are intentionally avoided here.
// NOTE: this template is served raw (no Python .format() call). Object
// literals must use single braces; blocks may use doubled braces — they
// parse as nested blocks and are functionally equivalent.
var STORAGE_KEY = 'kimi.sessionToken';
var _token = '';
(function () {
  try {
    var u = new URLSearchParams(window.location.search);
    var t = u.get('token');
    if (t) {
      _token = t;
      try { sessionStorage.setItem(STORAGE_KEY, t); } catch (_) {}
      u.delete('token');
      var remaining = u.toString();
      var clean = window.location.pathname + (remaining ? '?' + remaining : '') + window.location.hash;
      window.history.replaceState({}, document.title, clean);
    } else {
      try { _token = sessionStorage.getItem(STORAGE_KEY) || ''; } catch (_) { _token = ''; }
    }
  } catch (_) { _token = ''; }
})();
function authFetch(path) {
  var opts = { headers: {} };
  if (_token) opts.headers['Authorization'] = 'Bearer ' + _token;
  return fetch(path, opts);
}
async function load() {{
  const [statsRes, timelineRes] = await Promise.all([
    authFetch('/api/analytics/feeder-stats'),
    authFetch('/api/analytics/timeline'),
  ]);
  const stats = await statsRes.json();
  const tl = (await timelineRes.json()).events;

  const s = stats.feeder;
  const c = stats.completer;
  const e = stats.errors;

  let html = '';
  html += '<h2>Feeder</h2><div class="grid">';
  html += card('Turns Processed', s.total_turns_processed);
  html += card('Injections', s.injections, s.total_injection_bytes + ' bytes');
  html += card('Classifications', s.classifications.total, 'total');
  html += card('Matched', s.classifications.matched, 'by LLM', 'good');
  html += card('Empty / No Match', s.classifications.empty, '', 'warn');
  html += card('Cache Hits', s.cache_hits, '');
  html += card('Classify Errors', s.classifications.failed, '', s.classifications.failed > 0 ? 'bad' : '');
  html += '</div>';

  html += '<h2>Completer</h2><div class="grid">';
  const cr = c.completed > 0 ? (c.completed / (c.starts || 1) * 100).toFixed(0) : 0;
  html += card('Starts', c.starts);
  html += card('Completed', c.completed, cr + '% success', 'good');
  html += card('Failed', c.failed, '', c.failed > 0 ? 'bad' : '');
  html += card('Skipped', c.skipped, '');
  html += '</div>';

  html += '<h2>Matched Knowledge Entries</h2>';
  if (s.matched_knowledge_entries.length) {{
    html += '<div class="card"><div class="sub">' + s.matched_knowledge_entries.join(', ') + '</div></div>';
  }} else {{
    html += '<div class="card"><div class="sub">No entries matched yet</div></div>';
  }}

  html += '<h2>Event Timeline</h2><div class="card timeline">';
  for (const ev of tl) {{
    const cls = ev.event.includes('FAILED') ? '_3' : ev.event.includes('DONE') || ev.event.includes('INJECT') ? '_1' : ev.event.includes('SKIP') ? '_2' : '_0';
    html += '<div><span class="time">' + ev.time.slice(11, 19) + '</span> <span class="' + cls + '">' + ev.event + '</span> ' + ev.detail.slice(0, 80) + '</div>';
  }}
  html += '</div>';

  document.getElementById('root').innerHTML = html;
}}
function card(label, value, sub, cls) {{
  return '<div class="card"><div class="label">' + label + '</div><div class="value ' + (cls || '') + '">' + value + '</div>' + (sub ? '<div class="sub">' + sub + '</div>' : '') + '</div>';
}}
load();
</script>
</body>
</html>
"""


@router.get("/feeder-stats", include_in_schema=False)
async def feeder_stats_page():
    """Serve the analytics HTML page."""
    return HTMLResponse(_HTML_PAGE)
