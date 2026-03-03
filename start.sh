#!/bin/bash
# ============================================
# Scanner OSINT — Lancement automatique
# Backend (port 8001) + Frontend (port 3001)
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
LOG_DIR="$SCRIPT_DIR/logs"

mkdir -p "$LOG_DIR"

echo "=============================="
echo "  Scanner OSINT — Demarrage"
echo "=============================="
echo ""

# Kill existing processes on our ports
echo "[1/4] Nettoyage des ports..."
lsof -ti:8001 | xargs kill -9 2>/dev/null
lsof -ti:3001 | xargs kill -9 2>/dev/null
sleep 1

# Start backend
echo "[2/4] Lancement du backend (port 8001)..."
cd "$BACKEND_DIR"
python3 -m uvicorn app.main:app --port 8001 --host 0.0.0.0 > "$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Wait for backend to be ready
echo "  Attente du backend..."
for i in $(seq 1 15); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "  Backend OK!"
        break
    fi
    sleep 1
done

# Enable auto collection
echo "[3/4] Activation de la collecte automatique..."
curl -s -X PUT http://localhost:8001/api/intelligence/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "collection_interval_seconds": 600}' > /dev/null 2>&1
echo "  Collecte auto activee (toutes les 10 min)"

# First collection
echo "  Premiere collecte en cours..."
STATS=$(curl -s -X POST http://localhost:8001/api/intelligence/collect 2>/dev/null)
echo "  $STATS"

# Start frontend
echo "[4/4] Lancement du frontend (port 3001)..."
cd "$FRONTEND_DIR"
npx next start -p 3001 > "$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

# Save PIDs for stop script
echo "$BACKEND_PID" > "$LOG_DIR/backend.pid"
echo "$FRONTEND_PID" > "$LOG_DIR/frontend.pid"

sleep 2

echo ""
echo "=============================="
echo "  Scanner OSINT — En ligne!"
echo "=============================="
echo ""
echo "  Dashboard:  http://localhost:3001"
echo "  API:        http://localhost:8001/docs"
echo "  Logs:       $LOG_DIR/"
echo ""
echo "  Pour arreter: ./stop.sh"
echo ""

# Open browser
open http://localhost:3001 2>/dev/null

# Keep script alive to show logs
echo "Logs backend en direct (Ctrl+C pour arreter):"
echo "---"
tail -f "$LOG_DIR/backend.log"
