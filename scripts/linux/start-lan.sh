#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

if [[ ! -x "$BACKEND/.venv/bin/python" || ! -d "$FRONTEND/node_modules" ]]; then
  "$ROOT/scripts/setup-local.sh"
fi

python_set_env_line() {
  local file="$1"
  local key="$2"
  local value="$3"
  "$BACKEND/.venv/bin/python" - "$file" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text(encoding="utf-8-sig").splitlines() if path.exists() else []
prefix = f"{key}="
found = False
next_lines = []
for line in lines:
    if line.startswith(prefix):
        next_lines.append(f"{key}={value}")
        found = True
    else:
        next_lines.append(line)
if not found:
    next_lines.append(f"{key}={value}")
path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
PY
}

python_set_env_line "$BACKEND/.env" "DATABASE_URL" "sqlite:///./dev_trading.db"
python_set_env_line "$BACKEND/.env" "CORS_ORIGIN_REGEX" '^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173$'
python_set_env_line "$FRONTEND/.env" "VITE_API_BASE_URL" ""

SERVER_IP="$(hostname -I | awk '{print $1}')"
echo "Starting LAN app..."
echo "Open from another WiFi device: http://${SERVER_IP:-SERVER_IP}:5173"

(
  cd "$BACKEND"
  "$BACKEND/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

sleep 2
cd "$FRONTEND"
npm run dev -- --host 0.0.0.0 --port 5173
