from __future__ import annotations

import os
from pathlib import Path

SHARE_DIR_NAME = ".pc-kimi"
DEFAULT_PORT = 5496


def get_share_dir() -> Path:
    if share_dir := os.getenv("KIMI_SHARE_DIR"):
        share_dir = Path(share_dir)
    else:
        share_dir = Path.home() / SHARE_DIR_NAME
    share_dir.mkdir(parents=True, exist_ok=True)
    return share_dir


def get_sessions_root() -> Path:
    return get_share_dir() / "sessions"
