#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "Updating AI Crypto Trading Assistant without recloning..."
echo "Project: $ROOT"

if [[ ! -d ".git" ]]; then
  echo "This folder is not a git repository. Clone it once, then use this updater afterwards."
  exit 1
fi

if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Tracked local changes detected. Commit or stash them before updating."
  git status --short
  exit 1
fi

git pull --ff-only

chmod +x scripts/*.sh scripts/linux/*.sh
"$ROOT/scripts/setup-local.sh"

cd "$ROOT/frontend"
npm run build

if systemctl list-unit-files ai-crypto-backend.service >/dev/null 2>&1; then
  sudo systemctl daemon-reload
  sudo systemctl restart ai-crypto-backend.service
else
  echo "ai-crypto-backend.service is not installed yet."
fi

if systemctl list-unit-files ai-crypto-frontend.service >/dev/null 2>&1; then
  sudo systemctl restart ai-crypto-frontend.service
else
  echo "ai-crypto-frontend.service is not installed yet."
fi

"$ROOT/scripts/linux/check-lan-ports.sh"

echo
echo "Update complete."
