#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

if command -v python3.12 >/dev/null 2>&1; then
  PYTHON="python3.12"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "Python 3.12+ is required."
  echo "On Linux Mint: sudo apt update && sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

if ! "$PYTHON" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
then
  echo "Python 3.10+ is required, Python 3.12+ recommended."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Node.js/npm is required."
  echo "On Linux Mint, install Node.js LTS from NodeSource or your package manager."
  exit 1
fi

set_env_line() {
  local file="$1"
  local key="$2"
  local value="$3"
  "$PYTHON" - "$file" "$key" "$value" <<'PY'
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

new_secret() {
  "$PYTHON" - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
}

echo "Preparing local Linux Mint development environment..."

if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

if [[ ! -f "$FRONTEND/.env" ]]; then
  cp "$FRONTEND/.env.example" "$FRONTEND/.env"
fi

set_env_line "$BACKEND/.env" "DATABASE_URL" "sqlite:///./dev_trading.db"
set_env_line "$BACKEND/.env" "CORS_ORIGINS" "http://localhost:5173,http://127.0.0.1:5173"

if grep -q '^ADMIN_PASSWORD=change-this-password$' "$BACKEND/.env"; then
  set_env_line "$BACKEND/.env" "ADMIN_PASSWORD" "$(new_secret)"
fi

if grep -q '^AUTH_SECRET_KEY=change-this-long-random-secret$' "$BACKEND/.env"; then
  set_env_line "$BACKEND/.env" "AUTH_SECRET_KEY" "$(new_secret)"
fi

if [[ ! -d "$BACKEND/.venv" ]]; then
  "$PYTHON" -m venv "$BACKEND/.venv"
fi

"$BACKEND/.venv/bin/python" -m pip install --upgrade pip
"$BACKEND/.venv/bin/python" -m pip install -r "$BACKEND/requirements.txt"

cd "$FRONTEND"
npm install

echo
echo "Local setup complete."
echo "Run: ./scripts/start-local.sh"
