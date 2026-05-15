#!/usr/bin/env bash
# Flush all Kimi Code CLI log files.
#
# This removes:
#   - Application logs   (default: ~/.pc-kimi/logs/pc-kimi.log + rotated files)
#   - Test logs          (default: ~/.pc-kimi/logs/test_logs.jsonl)
#   - Review logs        (default: ~/.pc-kimi/logs/review/review_*.jsonl)
#
# Environment variables respected:
#   KIMI_SHARE_DIR      - overrides the share directory (default: ~/.pc-kimi)
#   KIMI_TEST_LOG_FILE  - overrides the test log file  (default: ~/.pc-kimi/logs/test_logs.jsonl)
#
# Usage:
#   ./scripts/flush_logs.sh        # delete logs
#   ./scripts/flush_logs.sh --dry-run   # preview what would be deleted

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

SHARE_DIR="${KIMI_SHARE_DIR:-$HOME/.pc-kimi}"
TEST_LOG_FILE="${KIMI_TEST_LOG_FILE:-$HOME/.pc-kimi/logs/test_logs.jsonl}"

# Gather candidate log files
LOG_FILES=()

# 1. Application logs under share dir
APP_LOG_DIR="$SHARE_DIR/logs"
if [[ -d "$APP_LOG_DIR" ]]; then
    for f in "$APP_LOG_DIR"/pc-kimi.log "$APP_LOG_DIR"/pc-kimi.*.log; do
        if [[ -f "$f" ]]; then
            LOG_FILES+=("$f")
        fi
    done
fi

# 2. Test logs (explicit path + rotated neighbours in same dir)
if [[ -f "$TEST_LOG_FILE" ]]; then
    LOG_FILES+=("$TEST_LOG_FILE")
    # Also pick up rotated test logs if any
    TEST_LOG_DIR=$(dirname "$TEST_LOG_FILE")
    for f in "$TEST_LOG_DIR"/test_logs.*.jsonl; do
        if [[ -f "$f" ]]; then
            LOG_FILES+=("$f")
        fi
    done
fi

# 3. Review logs (per-invocation JSONL files under logs/review/)
REVIEW_LOG_DIR="$SHARE_DIR/logs/review"
if [[ -d "$REVIEW_LOG_DIR" ]]; then
    for f in "$REVIEW_LOG_DIR"/review_*.jsonl; do
        if [[ -f "$f" ]]; then
            LOG_FILES+=("$f")
        fi
    done
fi

# 4. Legacy ~/.kimi/logs/kimi.log + rotated files (older installs)
LEGACY_LOG_DIR="$HOME/.kimi/logs"
if [[ -d "$LEGACY_LOG_DIR" ]]; then
    for f in "$LEGACY_LOG_DIR"/kimi.log "$LEGACY_LOG_DIR"/kimi.*.log; do
        if [[ -f "$f" ]]; then
            LOG_FILES+=("$f")
        fi
    done
fi

# 5. Legacy test logs at old default path (older installs)
LEGACY_TEST_LOG="$HOME/.kimi/logs/test_logs.jsonl"
if [[ -f "$LEGACY_TEST_LOG" ]]; then
    LOG_FILES+=("$LEGACY_TEST_LOG")
    LEGACY_TEST_LOG_DIR=$(dirname "$LEGACY_TEST_LOG")
    for f in "$LEGACY_TEST_LOG_DIR"/test_logs.*.jsonl; do
        if [[ -f "$f" ]]; then
            LOG_FILES+=("$f")
        fi
    done
fi

# Deduplicate
UNIQUE_FILES=()
if (( ${#LOG_FILES[@]} )); then
    while IFS= read -r line; do
        UNIQUE_FILES+=("$line")
    done < <(printf '%s\n' "${LOG_FILES[@]}" | sort -u)
fi

if (( ${#UNIQUE_FILES[@]} == 0 )); then
    echo "No log files found. Nothing to flush."
    exit 0
fi

TOTAL_SIZE=0
for f in "${UNIQUE_FILES[@]}"; do
    size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
    TOTAL_SIZE=$((TOTAL_SIZE + size))
done

if $DRY_RUN; then
    echo "[DRY-RUN] Would delete ${#UNIQUE_FILES[@]} log file(s):"
    for f in "${UNIQUE_FILES[@]}"; do
        echo "  $f"
    done
    echo "Total size: $((TOTAL_SIZE / 1024)) KB"
    echo "Re-run without --dry-run to delete."
    exit 0
fi

echo "Deleting ${#UNIQUE_FILES[@]} log file(s) ($((TOTAL_SIZE / 1024)) KB total):"
for f in "${UNIQUE_FILES[@]}"; do
    echo "  $f"
    rm -f "$f"
done

echo "Done."
