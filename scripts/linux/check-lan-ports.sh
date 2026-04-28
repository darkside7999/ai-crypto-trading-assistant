#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo "AI Crypto Trading Assistant LAN check"
echo "Project: $ROOT"
echo "Server IP: ${SERVER_IP:-unknown}"
echo

echo "Systemd services:"
systemctl is-active ai-crypto-backend.service >/dev/null 2>&1 && echo "  backend:  active" || echo "  backend:  inactive"
systemctl is-active ai-crypto-frontend.service >/dev/null 2>&1 && echo "  frontend: active" || echo "  frontend: inactive"
echo

echo "Listening ports:"
if command -v ss >/dev/null 2>&1; then
  ss -ltnp 2>/dev/null | awk 'NR == 1 || /:8000|:5173/'
elif command -v lsof >/dev/null 2>&1; then
  lsof -nP -iTCP:8000 -iTCP:5173 -sTCP:LISTEN || true
else
  echo "  Install iproute2 or lsof to inspect listening ports."
fi
echo

echo "Local health checks:"
if command -v curl >/dev/null 2>&1; then
  echo -n "  backend /health: "
  curl -fsS --max-time 5 http://127.0.0.1:8000/health || echo "FAILED"
  echo
  echo -n "  frontend:        "
  curl -fsS --max-time 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:5173 || echo "FAILED"
  echo
else
  echo "  curl is not installed."
fi
echo

if command -v ufw >/dev/null 2>&1; then
  echo "UFW firewall status:"
  sudo ufw status numbered || true
  echo
fi

echo "Open from another WiFi device:"
echo "  http://${SERVER_IP:-IP_DEL_SERVIDOR}:5173"
echo
echo "Backend health from another WiFi device:"
echo "  http://${SERVER_IP:-IP_DEL_SERVIDOR}:8000/health"
