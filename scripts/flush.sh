#!/usr/bin/env bash
# Flush all Kimi Code CLI logs and sessions.
#
# This removes:
#   - Application logs   (default: ~/.pc-kimi/logs/pc-kimi.log + rotated files)
#   - Test logs          (default: ~/.pc-kimi/logs/test_logs.jsonl)
#   - Review logs        (default: ~/.pc-kimi/logs/review/review_*.jsonl)
#   - Session directories (default: ~/.pc-kimi/sessions/*)
#
# Environment variables respected:
#   KIMI_SHARE_DIR      - overrides the share directory (default: ~/.pc-kimi)
#   KIMI_TEST_LOG_FILE  - overrides the test log file  (default: ~/.pc-kimi/logs/test_logs.jsonl)
#
# Usage:
#   ./scripts/flush.sh              # delete logs + sessions
#   ./scripts/flush.sh --dry-run    # preview what would be deleted

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

SHARE_DIR="${KIMI_SHARE_DIR:-$HOME/.pc-kimi}"
TEST_LOG_FILE="${KIMI_TEST_LOG_FILE:-$HOME/.pc-kimi/logs/test_logs.jsonl}"

# Gather candidate files and directories
ITEMS=()

# --- Logs ---

# 1. Application logs under share dir
APP_LOG_DIR="$SHARE_DIR/logs"
if [[ -d "$APP_LOG_DIR" ]]; then
    for f in "$APP_LOG_DIR"/pc-kimi.log "$APP_LOG_DIR"/pc-kimi.*.log; do
        if [[ -f "$f" ]]; then
            ITEMS+=("$f")
        fi
    done
fi

# 2. Test logs (explicit path + rotated neighbours in same dir)
if [[ -f "$TEST_LOG_FILE" ]]; then
    ITEMS+=("$TEST_LOG_FILE")
    TEST_LOG_DIR=$(dirname "$TEST_LOG_FILE")
    for f in "$TEST_LOG_DIR"/test_logs.*.jsonl; do
        if [[ -f "$f" ]]; then
            ITEMS+=("$f")
        fi
    done
fi

# 3. Review logs (per-invocation JSONL files under logs/review/)
REVIEW_LOG_DIR="$SHARE_DIR/logs/review"
if [[ -d "$REVIEW_LOG_DIR" ]]; then
    for f in "$REVIEW_LOG_DIR"/review_*.jsonl; do
        if [[ -f "$f" ]]; then
            ITEMS+=("$f")
        fi
    done
fi

# 4. Legacy ~/.kimi/logs/kimi.log + rotated files (older installs)
LEGACY_LOG_DIR="$HOME/.kimi/logs"
if [[ -d "$LEGACY_LOG_DIR" ]]; then
    for f in "$LEGACY_LOG_DIR"/kimi.log "$LEGACY_LOG_DIR"/kimi.*.log; do
        if [[ -f "$f" ]]; then
            ITEMS+=("$f")
        fi
    done
fi

# 5. Legacy test logs at old default path (older installs)
LEGACY_TEST_LOG="$HOME/.kimi/logs/test_logs.jsonl"
if [[ -f "$LEGACY_TEST_LOG" ]]; then
    ITEMS+=("$LEGACY_TEST_LOG")
    LEGACY_TEST_LOG_DIR=$(dirname "$LEGACY_TEST_LOG")
    for f in "$LEGACY_TEST_LOG_DIR"/test_logs.*.jsonl; do
        if [[ -f "$f" ]]; then
            ITEMS+=("$f")
        fi
    done
fi

# --- Sessions ---
SESSIONS_DIR="$SHARE_DIR/sessions"
if [[ -d "$SESSIONS_DIR" ]]; then
    for d in "$SESSIONS_DIR"/*; do
        if [[ -d "$d" ]]; then
            ITEMS+=("$d")
        fi
    done
fi

# Deduplicate
UNIQUE_ITEMS=()
if (( ${#ITEMS[@]} )); then
    while IFS= read -r line; do
        UNIQUE_ITEMS+=("$line")
    done < <(printf '%s\n' "${ITEMS[@]}" | sort -u)
fi

if (( ${#UNIQUE_ITEMS[@]} == 0 )); then
    echo "No log files or session directories found. Nothing to flush."
    exit 0
fi

# Compute size: files use stat, directories use du
TOTAL_SIZE=0
FILE_COUNT=0
DIR_COUNT=0
for item in "${UNIQUE_ITEMS[@]}"; do
    if [[ -f "$item" ]]; then
        size=$(stat -f%z "$item" 2>/dev/null || stat -c%s "$item" 2>/dev/null || echo 0)
        TOTAL_SIZE=$((TOTAL_SIZE + size))
        FILE_COUNT=$((FILE_COUNT + 1))
    elif [[ -d "$item" ]]; then
        size=$(du -sk "$item" 2>/dev/null | awk '{print $1}' || echo 0)
        # du -sk gives KB; convert to bytes for uniform total
        TOTAL_SIZE=$((TOTAL_SIZE + size * 1024))
        DIR_COUNT=$((DIR_COUNT + 1))
    fi
done

if $DRY_RUN; then
    echo "[DRY-RUN] Would delete ${FILE_COUNT} log file(s) and ${DIR_COUNT} session directory(s):"
    for item in "${UNIQUE_ITEMS[@]}"; do
        echo "  $item"
    done
    echo "Total size: $((TOTAL_SIZE / 1024)) KB"
    echo "Re-run without --dry-run to delete."
    exit 0
fi

echo "Deleting ${FILE_COUNT} log file(s) and ${DIR_COUNT} session directory(s) ($((TOTAL_SIZE / 1024)) KB total):"
for item in "${UNIQUE_ITEMS[@]}"; do
    echo "  $item"
    if [[ -f "$item" ]]; then
        rm -f "$item"
    elif [[ -d "$item" ]]; then
        rm -rf "$item"
    fi
done

echo "Done."
