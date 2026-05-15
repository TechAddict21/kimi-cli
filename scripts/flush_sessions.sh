#!/usr/bin/env bash
# Flush all Kimi Code CLI sessions.
#
# This removes:
#   - Session directories  (default: ~/.pc-kimi/sessions/*)
#
# Environment variables respected:
#   KIMI_SHARE_DIR  - overrides the share directory (default: ~/.pc-kimi)
#
# Usage:
#   ./scripts/flush_sessions.sh        # delete sessions
#   ./scripts/flush_sessions.sh --dry-run   # preview what would be deleted

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
fi

SHARE_DIR="${KIMI_SHARE_DIR:-$HOME/.pc-kimi}"
SESSIONS_DIR="$SHARE_DIR/sessions"

# Gather candidate session directories
SESSION_DIRS=()

if [[ -d "$SESSIONS_DIR" ]]; then
    for d in "$SESSIONS_DIR"/*; do
        if [[ -d "$d" ]]; then
            SESSION_DIRS+=("$d")
        fi
    done
fi

# Deduplicate (belt-and-suspenders)
UNIQUE_DIRS=()
if (( ${#SESSION_DIRS[@]} )); then
    while IFS= read -r line; do
        UNIQUE_DIRS+=("$line")
    done < <(printf '%s\n' "${SESSION_DIRS[@]}" | sort -u)
fi

if (( ${#UNIQUE_DIRS[@]} == 0 )); then
    echo "No session directories found. Nothing to flush."
    exit 0
fi

TOTAL_SIZE=0
for d in "${UNIQUE_DIRS[@]}"; do
    size=$(du -sk "$d" 2>/dev/null | awk '{print $1}' || echo 0)
    TOTAL_SIZE=$((TOTAL_SIZE + size))
done

if $DRY_RUN; then
    echo "[DRY-RUN] Would delete ${#UNIQUE_DIRS[@]} session directory(s):"
    for d in "${UNIQUE_DIRS[@]}"; do
        echo "  $d"
    done
    echo "Total size: ${TOTAL_SIZE} KB"
    echo "Re-run without --dry-run to delete."
    exit 0
fi

echo "Deleting ${#UNIQUE_DIRS[@]} session directory(s) (${TOTAL_SIZE} KB total):"
for d in "${UNIQUE_DIRS[@]}"; do
    echo "  $d"
    rm -rf "$d"
done

echo "Done."
