#!/bin/bash
# ============================================
# Scanner OSINT — Arret
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"

echo "Arret du Scanner OSINT..."

# Kill by saved PIDs
if [ -f "$LOG_DIR/backend.pid" ]; then
    kill $(cat "$LOG_DIR/backend.pid") 2>/dev/null
    rm "$LOG_DIR/backend.pid"
    echo "  Backend arrete"
fi

if [ -f "$LOG_DIR/frontend.pid" ]; then
    kill $(cat "$LOG_DIR/frontend.pid") 2>/dev/null
    rm "$LOG_DIR/frontend.pid"
    echo "  Frontend arrete"
fi

# Also kill by port (safety net)
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3001 | xargs kill -9 2>/dev/null

echo "Scanner OSINT arrete."
