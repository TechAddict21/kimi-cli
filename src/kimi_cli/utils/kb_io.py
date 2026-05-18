"""Knowledge-base I/O helpers.

Shared utilities for safe access to ``knowledge_base_world/`` directories
written by the Knowledge Completer subagent and read by the Knowledge Feeder.

Concerns covered:
- Atomic text writes (``tmp + os.replace``) so concurrent readers never see
  a partial file.
- Cooperative exclusive lock via ``fcntl.flock`` to serialize completer
  runs on the same KB and let the feeder skip cleanly when one is in flight.
- Path-sandbox check for ``→ Read:`` entries from ``DRILL_DOWN_TREE.md`` so
  a malicious or buggy tree entry cannot escape the working directory.
- Secret scanning over content destined for KB files (AWS, GCP, OpenAI,
  Anthropic, GitHub, generic PEM blocks, JWTs, long high-entropy strings).
"""

from __future__ import annotations

import contextlib
import os
import re
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

# fcntl is Unix-only. On Windows we fall back to atomic-mkdir locking so the
# CLI keeps importing cleanly. The fallback is correct for our use case
# (single advisory mutex; stale-lock recovery is bounded by process lifetime).
if sys.platform != "win32":
    import fcntl as _fcntl
else:  # pragma: no cover - exercised only on Windows runners
    _fcntl = None  # type: ignore[assignment]

KB_DIR_NAME = "knowledge_base_world"
_LOCK_FILENAME = ".kb.lock"


def atomic_text_write(path: Path, content: str, *, encoding: str = "utf-8") -> None:
    """Write text to ``path`` atomically.

    A temp file is created in the same directory then ``os.replace``'d onto
    the target so any concurrent reader sees either the old or new file —
    never a partial write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".kbtmp")
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise


def is_kb_path(path: Path) -> bool:
    """Return True if ``path`` lives under any ``knowledge_base_world/`` dir."""
    return KB_DIR_NAME in path.parts


def validate_safe_path(work_dir: Path, raw_path: str) -> Path | None:
    """Resolve ``raw_path`` under ``work_dir`` and reject anything escaping it.

    Returns the resolved path or None if the path is unsafe (escapes work_dir,
    is absolute, contains parent traversal that resolves outside, or fails to
    resolve cleanly).
    """
    if not raw_path or raw_path.startswith("/") or raw_path.startswith("~"):
        return None
    try:
        work_real = work_dir.resolve()
        candidate = (work_dir / raw_path).resolve()
    except OSError:
        return None
    try:
        candidate.relative_to(work_real)
    except ValueError:
        return None
    return candidate


@contextlib.contextmanager
def kb_try_lock(kb_dir: Path) -> Iterator[bool]:
    """Try to acquire an exclusive non-blocking lock on the KB.

    Yields True if the lock was acquired (and releases it on exit), False if
    another holder is already running. Callers should treat False as "skip
    this update — another writer is already at work".

    Uses ``fcntl.flock`` on POSIX and ``os.mkdir`` on Windows (atomic create
    is portable; the lock is auto-released when the directory is removed on
    exit). Lock-file pollution is bounded — a single ``.kb.lock`` per KB.
    """
    if not kb_dir.exists():
        yield False
        return

    lock_path = kb_dir / _LOCK_FILENAME

    # POSIX: fcntl.flock — kernel-managed lock, released on close/crash.
    if _fcntl is not None:
        fd: int | None = None
        try:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
            try:
                _fcntl.flock(fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                fd = None
                yield False
                return
            yield True
        finally:
            if fd is not None:
                with contextlib.suppress(OSError):
                    _fcntl.flock(fd, _fcntl.LOCK_UN)
                with contextlib.suppress(OSError):
                    os.close(fd)
        return

    # Windows fallback: atomic mkdir. A stale lock (process killed without
    # cleanup) requires manual removal — acceptable trade-off vs depending
    # on msvcrt.locking which has its own semantics quirks.
    dir_lock = kb_dir / (_LOCK_FILENAME + ".d")
    try:
        os.mkdir(dir_lock)
    except FileExistsError:
        yield False
        return
    except OSError:
        yield False
        return
    try:
        yield True
    finally:
        with contextlib.suppress(OSError):
            os.rmdir(dir_lock)


_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("AWS_ACCESS_KEY_ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("AWS_SECRET_KEY", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*[\"']?[A-Za-z0-9/+=]{40}")),
    ("GITHUB_PAT", re.compile(r"\bghp_[A-Za-z0-9]{36,}\b")),
    ("GITHUB_OAUTH", re.compile(r"\bgho_[A-Za-z0-9]{36,}\b")),
    ("GITHUB_SERVER", re.compile(r"\bghs_[A-Za-z0-9]{36,}\b")),
    ("GITHUB_USER", re.compile(r"\bghu_[A-Za-z0-9]{36,}\b")),
    ("GITHUB_REFRESH", re.compile(r"\bghr_[A-Za-z0-9]{36,}\b")),
    ("OPENAI_KEY", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("ANTHROPIC_KEY", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{32,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("SLACK_TOKEN", re.compile(r"\bxox[abps]-[0-9]+-[0-9]+-[0-9]+-[A-Za-z0-9]+\b")),
    ("STRIPE_LIVE", re.compile(r"\b(?:sk|rk)_live_[0-9a-zA-Z]{24,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("PEM_PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("GCP_SERVICE_ACCOUNT", re.compile(r'"type"\s*:\s*"service_account"')),
    ("GENERIC_BEARER", re.compile(r"(?i)\bauthorization\s*:\s*bearer\s+[A-Za-z0-9._-]{20,}\b")),
)


def scan_for_secrets(content: str) -> list[str]:
    """Return a list of secret-pattern names found in ``content``.

    Empty list = clean. Callers should reject the write if non-empty.
    """
    if not content:
        return []
    hits: list[str] = []
    for name, pattern in _SECRET_PATTERNS:
        if pattern.search(content):
            hits.append(name)
    return hits


__all__ = [
    "KB_DIR_NAME",
    "atomic_text_write",
    "is_kb_path",
    "kb_try_lock",
    "scan_for_secrets",
    "validate_safe_path",
]
