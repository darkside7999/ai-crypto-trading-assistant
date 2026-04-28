#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND="$ROOT/frontend"

if [[ ! -f "$FRONTEND/.env" ]]; then
  cp "$FRONTEND/.env.example" "$FRONTEND/.env"
fi

if [[ ! -d "$FRONTEND/node_modules" ]]; then
  echo "Frontend dependencies not found. Running npm install..."
  cd "$FRONTEND"
  npm install
fi

cd "$FRONTEND"
echo "Frontend: http://127.0.0.1:5173"
npm run dev -- --host 127.0.0.1 --port 5173
