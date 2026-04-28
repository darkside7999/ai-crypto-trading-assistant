#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
fi

if [[ ! -x "$BACKEND/.venv/bin/python" ]]; then
  echo "Backend virtualenv not found. Running setup-local.sh first..."
  "$ROOT/scripts/setup-local.sh"
fi

cd "$BACKEND"
echo "Backend: http://127.0.0.1:8000"
"$BACKEND/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
