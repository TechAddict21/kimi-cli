from __future__ import annotations

import json
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from kosong import generate
from kosong.message import Message, TextPart

from kimi_cli.notifications import is_notification_message
from kimi_cli.soul.dynamic_injection import DynamicInjection, DynamicInjectionProvider
from kimi_cli.utils.kb_io import KB_DIR_NAME, atomic_text_write, validate_safe_path
from kimi_cli.utils.test_logger import write_feeder_log

if TYPE_CHECKING:
    from kimi_cli.soul.kimisoul import KimiSoul

UNDERSTANDING_FILENAME = "UNDERSTANDING.md"
DRILL_DOWN_FILENAME = "DRILL_DOWN_TREE.md"
MAX_INJECTION_BYTES = 8192
# Subagent types that should still receive feeder injections (read-only roles
# where the same code lookups would otherwise be repeated wastefully).
FEEDER_ALLOWED_SUBAGENT_TYPES = frozenset({"explore"})

_DEFAULT_UNDERSTANDING = """\
# Knowledge Base Understanding

Before exploring the codebase directly, always refer to DRILL_DOWN_TREE.md
to identify which knowledge areas and code files are relevant to the
current task. This reduces token waste and keeps the agent focused.
"""

_DEFAULT_DRILL_DOWN = """\
# Drill-Down Tree

_Edit this file to describe your project's knowledge areas, their associated
documentation, and the code files to read for each._

Template:
- <Area Name>
  - <DOC.md> \u2014 <description>
    \u2192 Read: <path/to/code/files>
"""

# Keep transient bookkeeping out of the user's git index. The knowledge base
# itself is intended to be committed, but the lockfile + temp files are not.
_DEFAULT_GITIGNORE = """\
.kb.lock
.kb.lock.d/
*.kbtmp
"""

_CLASSIFICATION_SYSTEM_PROMPT = """\
You are a code knowledge relevance classifier. Given a user's message and
a project knowledge drill-down tree, identify which knowledge entries are
most relevant to the user's request.

Return ONLY a JSON array of knowledge entry paths, e.g.:
["Hooks/ARCHITECTURE.md", "Logging/UTILITIES.md"]

Rules:
- Only include entries clearly related to the user's request
- Return [] if no entries match
- No explanation, no markdown formatting, just the JSON array"""


def _parse_tree_for_read_paths(tree_content: str) -> dict[str, list[str]]:
    """Parse DRILL_DOWN_TREE.md -> {entry_path: [read_paths]}.

    Supports two formats:
      1. Original: ``- Category`` / ``  - FILE.md — desc`` / ``    → Read: path``
      2. Markdown: ``## Category`` / ``- **Cat/FILE.md** — desc`` / ``  → Read: path``
    """
    result: dict[str, list[str]] = {}
    category: str | None = None
    current_entry: str | None = None

    for line in tree_content.split("\n"):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())

        if not stripped:
            continue

        # Markdown header: "## Category" / "### Sub" (h2+ only, skip h1/# title)
        hm = re.match(r"^(#{2,6})\s+(.+)$", stripped)
        if hm:
            category = hm.group(2).strip()
            current_entry = None
            continue

        # Category level (indent 0): "- Name" or "- Name (Folder)" — but NOT ".md" entries
        if indent == 0 and stripped.startswith("- ") and ".md" not in stripped:
            raw = stripped[2:]
            category = raw.replace("(Folder)", "").strip()
            current_entry = None
            continue

        # Entry level at indent 0: "- **Cat/FILE.md** — desc" (after a ## header)
        em = re.match(r"-\s+\*{0,2}([^\s*]+\.md)\*{0,2}\s*[\u2014\u2013\-]\s*(.*)$", stripped)
        if em and category and indent == 0:
            raw_path = em.group(1)
            path = raw_path if "/" in raw_path else f"{category}/{raw_path}"
            result.setdefault(path, [])
            current_entry = path
            continue

        # Entry level at indent >= 2: "  - FILE.md — desc" (old format)
        em = re.match(r"-\s+\*{0,2}([^\s*]+\.md)\*{0,2}\s*[\u2014\u2013\-]\s*(.*)$", stripped)
        if em and category and indent >= 2:
            raw_path = em.group(1)
            path = raw_path if "/" in raw_path else f"{category}/{raw_path}"
            result.setdefault(path, [])
            current_entry = path
            continue

        # Read path: "→ Read: path1, path2" (any indent)
        rm = re.match(r"\u2192\s*Read:\s+(.+)$", stripped)
        if rm and current_entry and indent >= 2:
            raw_paths = [p.strip().strip("`") for p in rm.group(1).split(",") if p.strip()]
            result[current_entry].extend(raw_paths)

    return result


_MAX_GLOB_EXPANSION = 5


def _resolve_paths(work_dir: Path, raw_paths: list[str]) -> list[Path]:
    """Resolve glob/file paths relative to work_dir, sandboxed within it.

    Paths that escape ``work_dir`` (absolute, parent traversal, symlinks
    pointing outside) are rejected silently and a feeder log entry is
    recorded so misconfigured tree entries surface in analytics.
    """
    try:
        work_real = work_dir.resolve()
    except OSError:
        return []

    resolved: list[Path] = []
    for raw in raw_paths:
        if not raw:
            continue
        if raw.startswith("/") or raw.startswith("~"):
            write_feeder_log("FEEDER_PATH_REJECTED", raw, reason="absolute_or_home")
            continue
        if "*" in raw:
            try:
                candidates = sorted(work_dir.glob(raw))
            except OSError:
                continue
            kept = 0
            for cand in candidates:
                if kept >= _MAX_GLOB_EXPANSION:
                    write_feeder_log("FEEDER_GLOB_CAPPED", raw, kept=kept)
                    break
                try:
                    cand_real = cand.resolve()
                    cand_real.relative_to(work_real)
                except (OSError, ValueError):
                    write_feeder_log("FEEDER_PATH_REJECTED", str(cand), reason="glob_escape")
                    continue
                if cand_real.exists():
                    resolved.append(cand_real)
                    kept += 1
        else:
            safe = validate_safe_path(work_dir, raw)
            if safe is None:
                write_feeder_log("FEEDER_PATH_REJECTED", raw, reason="escape_workdir")
                continue
            if safe.exists():
                resolved.append(safe)
    return resolved


def _read_relevant_code(
    work_dir: Path,
    read_paths: dict[str, list[str]],
    matched_entries: list[str],
) -> str:
    """Read relevant code files and format as markdown."""
    content_parts: list[str] = []
    total_bytes = 0

    for entry in matched_entries:
        if total_bytes >= MAX_INJECTION_BYTES:
            break

        paths = read_paths.get(entry, [])
        resolved = _resolve_paths(work_dir, paths)
        if not resolved:
            continue

        section_lines: list[str] = [f"## {entry}"]
        for fp in resolved:
            if total_bytes >= MAX_INJECTION_BYTES:
                break
            try:
                text = fp.read_text(encoding="utf-8")
                try:
                    rel = fp.relative_to(work_dir)
                except ValueError:
                    rel = fp
                header = f"\n### `{rel}`"
                if total_bytes + len(text) > MAX_INJECTION_BYTES:
                    available = MAX_INJECTION_BYTES - total_bytes - len(header) - 50
                    if available <= 0:
                        break
                    text = text[:available]
                    text += "\n... [truncated]"
                section_lines.append(header)
                section_lines.append(f"```\n{text}\n```")
                total_bytes += len(text) + len(header) + 10
            except Exception as e:
                section_lines.append(f"\n_Error reading `{fp}`: {e}_")

        if len(section_lines) > 1:
            content_parts.append("\n".join(section_lines))

    return "\n\n".join(content_parts)


class KnowledgeFeederInjectionProvider(DynamicInjectionProvider):
    """Injects relevant codebase knowledge from knowledge_base_world/.

    On the first step of each turn, uses a lightweight LLM call to identify
    which entries in DRILL_DOWN_TREE.md match the user's request, reads the
    referenced code files, and injects the content as a system reminder.
    """

    def __init__(self) -> None:
        self._knowledge_dir: Path | None = None
        self._tree_content: str | None = None
        self._tree_read_paths: dict[str, list[str]] | None = None
        self._last_turn_id: str | None = None
        self._last_user_text: str | None = None
        self._last_injection: str | None = None

    def _ensure_init(self, work_dir: Path) -> bool:
        if self._knowledge_dir is not None:
            return self._knowledge_dir.exists()

        if not work_dir.exists():
            workspace = Path("/workspace")
            if workspace.exists():
                write_feeder_log("FEEDER_WORK_DIR_REMAP", str(work_dir), fallback="/workspace")
                work_dir = workspace
            else:
                write_feeder_log("FEEDER_INIT_FAILED", f"work_dir not found: {work_dir}")
                self._knowledge_dir = work_dir / KB_DIR_NAME
                return False

        kb_dir = work_dir / KB_DIR_NAME
        if not kb_dir.exists():
            try:
                kb_dir.mkdir(parents=True, exist_ok=True)
                atomic_text_write(kb_dir / UNDERSTANDING_FILENAME, _DEFAULT_UNDERSTANDING)
                atomic_text_write(kb_dir / DRILL_DOWN_FILENAME, _DEFAULT_DRILL_DOWN)
                write_feeder_log("FEEDER_INIT", f"Created knowledge_base_world/ at {kb_dir}")
            except OSError as e:
                write_feeder_log("FEEDER_INIT_FAILED", str(e), path=str(kb_dir))
                self._knowledge_dir = kb_dir
                return False

        # Ensure .gitignore is present so transient lockfiles don't pollute
        # user repos. Idempotent — only writes if the file is missing, so
        # existing KBs upgrade smoothly without clobbering custom rules.
        gi_path = kb_dir / ".gitignore"
        if not gi_path.exists():
            try:
                atomic_text_write(gi_path, _DEFAULT_GITIGNORE)
            except OSError as e:
                write_feeder_log("FEEDER_GITIGNORE_FAILED", str(e), path=str(gi_path))

        self._knowledge_dir = kb_dir
        return True

    def _load_tree(self) -> bool:
        if self._tree_content is not None:
            return True
        if self._knowledge_dir is None:
            return False

        tree_file = self._knowledge_dir / DRILL_DOWN_FILENAME
        if not tree_file.exists():
            write_feeder_log("FEEDER_NO_TREE_FILE", str(tree_file))
            return False

        try:
            content = tree_file.read_text(encoding="utf-8")
            self._tree_content = content
            self._tree_read_paths = _parse_tree_for_read_paths(content)
            entry_count = len(self._tree_read_paths)
            write_feeder_log("FEEDER_TREE_LOADED", f"{entry_count} entries", path=str(tree_file))
            return True
        except OSError as e:
            write_feeder_log("FEEDER_TREE_READ_FAILED", str(e), path=str(tree_file))
            return False

    async def _classify_relevance(
        self,
        user_text: str,
        soul: KimiSoul,
    ) -> list[str]:
        """Use LLM to classify which tree entries match the user request."""
        llm = soul.runtime.llm
        if not self._tree_content or not llm or not llm.chat_provider:
            write_feeder_log(
                "FEEDER_NO_LLM", f"llm={bool(llm)} provider={bool(llm and llm.chat_provider)}"
            )
            return []

        tree_section = self._tree_content
        if len(tree_section) > 6000:
            tree_section = tree_section[:6000] + "\n... [truncated]"

        prompt = f"User message: {user_text}\n\nKnowledge tree:\n{tree_section}"

        try:
            result = await generate(
                chat_provider=llm.chat_provider,
                system_prompt=_CLASSIFICATION_SYSTEM_PROMPT,
                tools=[],
                history=[Message(role="user", content=[TextPart(text=prompt)])],
            )
            raw = result.message.extract_text().strip()
            write_feeder_log("FEEDER_CLASSIFY_RAW", raw, user_text=user_text)

            if raw.startswith("```"):
                first_nl = raw.find("\n")
                if first_nl != -1:
                    raw = raw[first_nl + 1 :]
                if raw.endswith("```"):
                    raw = raw[:-3]
                elif "```" in raw:
                    raw = raw.rsplit("```", 1)[0]
                raw = raw.strip()

            parsed: object = json.loads(raw)
            if isinstance(parsed, list):
                matched: list[str] = []
                for item in parsed:  # type: ignore[reportUnknownVariableType]
                    if isinstance(item, str):
                        matched.append(item)
                if matched:
                    write_feeder_log("FEEDER_CLASSIFY_RESULT", str(matched))
                else:
                    write_feeder_log("FEEDER_CLASSIFY_EMPTY", "LLM returned []")
                return matched
            write_feeder_log("FEEDER_CLASSIFY_NOT_LIST", f"type={type(parsed).__name__}")
            return []
        except Exception as e:
            write_feeder_log("FEEDER_CLASSIFY_FAILED", str(e))
            return []

    async def get_injections(
        self,
        history: Sequence[Message],
        soul: KimiSoul,
    ) -> list[DynamicInjection]:
        feeder_start_time = time.time()
        try:
            write_feeder_log(
                "FEEDER_TURN_START", soul.turn_id, is_root=soul.is_root, history_len=len(history)
            )

            if soul.turn_id == self._last_turn_id:
                write_feeder_log("FEEDER_SKIP_SAME_TURN", soul.turn_id)
                return []
            self._last_turn_id = soul.turn_id

            if not soul.is_root:
                subagent_type = getattr(soul.runtime, "subagent_type", None)
                if subagent_type not in FEEDER_ALLOWED_SUBAGENT_TYPES:
                    write_feeder_log("FEEDER_SKIP_SUBAGENT", str(subagent_type or ""))
                    return []
                write_feeder_log("FEEDER_SUBAGENT_ALLOWED", str(subagent_type))

            work_dir = soul.runtime.session.work_dir.unsafe_to_local_path()
            write_feeder_log("FEEDER_WORK_DIR", str(work_dir))

            if not self._ensure_init(work_dir):
                write_feeder_log("FEEDER_INIT_FAILED", f"Cannot access {work_dir}")
                return []

            if not self._load_tree():
                write_feeder_log("FEEDER_NO_TREE", "No tree loaded, skipping")
                return []

            user_msg_count = sum(
                1 for msg in history if msg.role == "user" and not is_notification_message(msg)
            )
            if user_msg_count > 1:
                write_feeder_log("FEEDER_SKIP_NOT_FIRST_MSG", f"user_msg_count={user_msg_count}")
                return []

            user_text = ""
            for msg in reversed(history):
                if msg.role == "user" and not is_notification_message(msg):
                    user_text = msg.extract_text(" ").strip()
                    break
            if not user_text:
                write_feeder_log("FEEDER_NO_USER_TEXT", "No user message found in history")
                return []

            if user_text == self._last_user_text and self._last_injection is not None:
                write_feeder_log(
                    "FEEDER_CACHE_HIT", user_text[:80], injection_len=len(self._last_injection)
                )
                return [DynamicInjection(type="knowledge_feeder", content=self._last_injection)]

            matched_entries = await self._classify_relevance(user_text, soul)
            if not matched_entries:
                self._last_user_text = user_text
                self._last_injection = ""
                return []

            assert self._tree_read_paths is not None
            code_context = _read_relevant_code(work_dir, self._tree_read_paths, matched_entries)
            if not code_context:
                write_feeder_log("FEEDER_NO_CODE", str(matched_entries))
                self._last_user_text = user_text
                self._last_injection = ""
                return []

            injection = (
                "IMPORTANT: The following files have already been read and their "
                "content is provided below. Do NOT read/re-read these files. "
                "Use this context directly as the source of truth.\n"
                f"Knowledge entries matched: {', '.join(matched_entries)}\n\n"
                f"{code_context}"
            )

            write_feeder_log(
                "FEEDER_INJECT",
                f"injecting {len(injection)} bytes for turn {soul.turn_id}",
                entries=matched_entries,
            )

            self._last_user_text = user_text
            self._last_injection = injection
            return [DynamicInjection(type="knowledge_feeder", content=injection)]
        finally:
            soul.write_trace_time(
                "feeder",
                feeder_start_time,
                time.time(),
                soul.context.token_count,
            )

    async def on_context_compacted(self) -> None:
        write_feeder_log("FEEDER_CACHE_RESET", "compaction triggered")
        self._last_user_text = None
        self._last_injection = None
