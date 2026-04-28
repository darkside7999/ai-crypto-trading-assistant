#!/usr/bin/env bash
set -euo pipefail

PORTS=(8000 5173)
KILL_MODE="${1:-}"

echo "Stopping systemd services first..."
sudo systemctl stop ai-crypto-frontend.service 2>/dev/null || true
sudo systemctl stop ai-crypto-backend.service 2>/dev/null || true

echo
echo "Processes currently listening on LAN app ports:"
for port in "${PORTS[@]}"; do
  echo "Port $port:"
  if command -v fuser >/dev/null 2>&1; then
    sudo fuser -v "${port}/tcp" || true
  elif command -v lsof >/dev/null 2>&1; then
    sudo lsof -nP -iTCP:"$port" -sTCP:LISTEN || true
  else
    echo "  Install psmisc or lsof to inspect/kill port owners."
  fi
done

if [[ "$KILL_MODE" != "--kill" ]]; then
  echo
  echo "No process was killed."
  echo "To stop anything still occupying ports 8000/5173, run:"
  echo "  ./scripts/linux/free-lan-ports.sh --kill"
  exit 0
fi

echo
echo "Killing processes that still occupy ports 8000/5173..."
for port in "${PORTS[@]}"; do
  if command -v fuser >/dev/null 2>&1; then
    sudo fuser -k "${port}/tcp" || true
  elif command -v lsof >/dev/null 2>&1; then
    pids="$(sudo lsof -t -iTCP:"$port" -sTCP:LISTEN || true)"
    if [[ -n "$pids" ]]; then
      sudo kill $pids || true
    fi
  fi
done

echo "Ports released. You can restart with:"
echo "  ./scripts/linux/restart-systemd-lan.sh"
