#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"

echo "Restarting AI Crypto Trading Assistant LAN services..."

sudo systemctl daemon-reload
sudo systemctl restart ai-crypto-backend.service
sudo systemctl restart ai-crypto-frontend.service

sleep 3

echo
sudo systemctl --no-pager --lines=8 status ai-crypto-backend.service ai-crypto-frontend.service || true

echo
"$ROOT/scripts/linux/check-lan-ports.sh"

echo
echo "LAN URL:"
echo "  http://${SERVER_IP:-IP_DEL_SERVIDOR}:5173"
