#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "$ROOT/backend/.venv/bin/python" || ! -d "$ROOT/frontend/node_modules" ]]; then
  "$ROOT/scripts/setup-local.sh"
fi

echo "Starting backend and frontend..."
echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:5173"

"$ROOT/scripts/start-backend.sh" &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2
"$ROOT/scripts/start-frontend.sh"
